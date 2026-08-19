# Copyright 2026 Ritesh Ambastha
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Top-level pipeline orchestrator

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone

from pydub import AudioSegment

from redactguard_core.detectors.registry import run_detectors
from redactguard_core.ensemble.voting import vote
from redactguard_core.pipeline.ingest import decode_media, get_frame_rate, sample_frames
from redactguard_core.pipeline.manifest import RedactionManifest
from redactguard_core.pipeline.policy import PolicyProfile
from redactguard_core.pipeline.report import AuditReport, VerificationPass
from redactguard_core.redaction.audio import apply_audio_redactions
from redactguard_core.redaction.muxer import encode_video_from_frames, mux
from redactguard_core.redaction.visual import apply_visual_redactions
from redactguard_core.verification.retry_controller import RetryController
from redactguard_core.verification.verifier import Verifier

logger = logging.getLogger(__name__)


class Orchestrator:
    """Runs one file through: detect -> vote -> [scan stops here] -> redact
    -> verify -> retry -> report. See docs/architecture.md for the full
    pipeline diagram and docs/adr/ for why each stage exists.

    Every stage transition is reported two ways, both driven by the same
    `_report()` call so they can never drift out of sync: always via
    `logger.info()` (so `redactguard run`/`batch` show progress on stdout
    the moment logging is configured - see redactguard_cli.main), and
    additionally via `on_progress`, if given, for a caller (e.g.
    redactguard-webapp) that wants to surface the same messages somewhere
    other than a log stream, such as a job's live progress page - see
    docs/adr/0012. Without `on_progress` set, this call costs one no-op
    check per stage; there was no visibility into a long-running `run()`
    call before this - a multi-minute job just showed as "running" with
    nothing else to go on.
    """

    def __init__(
        self,
        policy: PolicyProfile,
        sample_fps: float = 1.0,
        on_progress: Callable[[str], None] | None = None,
    ):
        self.policy = policy
        self.sample_fps = sample_fps
        self.retry_controller = RetryController(policy.retry)
        self.verifier = Verifier()
        self.on_progress = on_progress

    def _report(self, message: str) -> None:
        logger.info(message)
        if self.on_progress is not None:
            self.on_progress(message)

    def scan(self, source_file: str) -> RedactionManifest:
        """Dry-run: decode + detect + vote, no video modified. This is the
        CLI's `redactguard scan` output.
        """
        self._report(f"Decoding {source_file} and sampling frames at {self.sample_fps} fps for detection")
        media = decode_media(source_file, fps=self.sample_fps)
        self._report("Running the detector ensemble")
        results = run_detectors(media, self.policy)
        self._report(f"Voting on {len(results)} raw detection(s) at agreement_threshold={self.policy.agreement_threshold}")
        spans = vote(results, self.policy.agreement_threshold)
        self._report(f"Scan complete: {len(spans)} trusted PII span(s)")
        return RedactionManifest(
            source_file=source_file,
            policy_profile=self.policy.name,
            created_at=datetime.now(timezone.utc),
            spans=spans,
        )

    def run(self, source_file: str, output_file: str) -> AuditReport:
        """Detect, redact, verify, retry-with-escalation, and report. This
        is the CLI's `redactguard run` - see
        docs/adr/0002-mandatory-verify-then-retry-loop.md for the overall
        design and docs/adr/0007 for why redaction compositing happens at
        the source's native frame rate rather than `sample_fps`.

        Detection runs exactly once against the original source; each
        retry only re-votes the same raw detections at a lower agreement
        threshold and re-composites with a wider margin (RetryController),
        rather than re-running the (expensive) detectors themselves. Only
        the *verification* pass after each redaction attempt re-decodes
        and re-detects - against the redacted draft, to confirm nothing
        was missed.

        Per ADR-0002, exhausting max_attempts never withholds output: the
        best (final) redacted draft is still written, with `unresolved`
        and `warnings` set on the returned AuditReport for human review.
        """
        self._report(f"Decoding {source_file} and sampling frames at {self.sample_fps} fps for detection")
        detection_media = decode_media(source_file, fps=self.sample_fps)
        self._report("Running the detector ensemble on the source video")
        raw_results = run_detectors(detection_media, self.policy)
        self._report(f"Detection complete: {len(raw_results)} raw detection(s) before voting")
        half_window_s = 0.5 / self.sample_fps

        native_fps = get_frame_rate(source_file)
        self._report(f"Decoding {source_file} at its native {native_fps:.3g} fps for redaction compositing")
        native_workdir = tempfile.mkdtemp(prefix="redactguard-native-")
        native_frames = sample_frames(source_file, native_workdir, fps=native_fps)

        original_audio = None
        if detection_media.audio_path:
            original_audio = AudioSegment.from_wav(detection_media.audio_path)

        workdir = tempfile.mkdtemp(prefix="redactguard-run-")
        os.makedirs(os.path.dirname(os.path.abspath(output_file)) or ".", exist_ok=True)

        verification_passes: list[VerificationPass] = []
        attempt = 0
        threshold = self.policy.agreement_threshold
        margin_px = self.retry_controller.base_margin_px
        last_draft_path: str | None = None
        manifest: RedactionManifest | None = None

        while True:
            spans = vote(raw_results, threshold)
            self._report(
                f"Attempt {attempt + 1}: voting at agreement_threshold={threshold} -> {len(spans)} trusted span(s)"
            )
            manifest = RedactionManifest(
                source_file=source_file,
                policy_profile=self.policy.name,
                created_at=datetime.now(timezone.utc),
                spans=spans,
            )

            visual_spans = [s for s in spans if s.bbox is not None]
            audio_spans = [s for s in spans if s.pii_type == "audio"]

            self._report(
                f"Attempt {attempt + 1}: redacting {len(visual_spans)} visual span(s) and "
                f"{len(audio_spans)} audio span(s) across {len(native_frames)} native-fps frame(s)"
            )
            redacted_frames = apply_visual_redactions(native_frames, visual_spans, half_window_s, margin_px)
            video_only_path = os.path.join(workdir, f"attempt{attempt}.video.mp4")
            encode_video_from_frames(redacted_frames, native_fps, video_only_path)

            redacted_audio_path = None
            if original_audio is not None:
                redacted_audio_path = os.path.join(workdir, f"attempt{attempt}.audio.wav")
                apply_audio_redactions(original_audio, audio_spans).export(redacted_audio_path, format="wav")

            draft_path = os.path.join(workdir, f"attempt{attempt}.draft.mp4")
            mux(video_only_path, redacted_audio_path, draft_path)
            last_draft_path = draft_path

            self._report(f"Attempt {attempt + 1}: re-scanning the redacted draft to verify nothing was missed")
            verify_media = decode_media(draft_path, fps=self.sample_fps)
            verify_spans = self.verifier.verify(verify_media, self.policy, agreement_threshold=1)
            verification_passes.append(
                VerificationPass(attempt=attempt, spans_still_flagged=len(verify_spans), escalated=attempt > 0)
            )

            if not verify_spans:
                self._report(f"Attempt {attempt + 1}: verification clean - writing final output")
                shutil.copyfile(last_draft_path, output_file)
                return AuditReport(manifest=manifest, verification_passes=verification_passes, unresolved=False)

            self._report(
                f"Attempt {attempt + 1}: verifier still flagged {len(verify_spans)} span(s) - escalating"
            )
            try:
                escalated = self.retry_controller.escalate(attempt)
            except RuntimeError:
                self._report(
                    f"Retry attempts exhausted ({self.policy.retry.max_attempts}) - writing the best draft "
                    "anyway and flagging it unresolved for human review"
                )
                shutil.copyfile(last_draft_path, output_file)
                return AuditReport(
                    manifest=manifest,
                    verification_passes=verification_passes,
                    unresolved=True,
                    warnings=[
                        (
                            f"{len(verify_spans)} PII span(s) still flagged by the verifier after "
                            f"{self.policy.retry.max_attempts} redaction attempt(s). Output was still "
                            "written (RedactGuard never withholds output - see ADR-0002); route this "
                            "file to human review before distributing it."
                        )
                    ],
                )
            threshold, margin_px, attempt = escalated.agreement_threshold, escalated.blur_margin_px, escalated.attempt


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
