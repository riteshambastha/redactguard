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
End-to-end tests for Orchestrator.run() - the full detect -> redact ->
verify -> retry -> report closed loop, against real ffmpeg-generated video.

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

import os
import subprocess

from redactguard_core.pipeline.ingest import has_audio_stream
from redactguard_core.pipeline.orchestrator import Orchestrator
from redactguard_core.pipeline.policy import PiiTypeConfig, PolicyProfile, RetryConfig

# agreement_threshold=2 mirrors the real profiles (policies/gdpr_v1.yaml
# etc.) now that text has two independent detectors (Tesseract OCR + MSER
# structural region proposal - see docs/adr/0008). Note that Tesseract's
# word-level OCR bbox and MSER's finer sub-word regions don't always
# spatially overlap enough to agree on the *first* pass over real text -
# ADR-0008 documents why, and why the retry/escalation loop (which
# progressively lowers the threshold) is what makes that non-fatal rather
# than a design bug; max_attempts=3 gives it room to actually converge.
_POLICY = PolicyProfile(
    version=1,
    name="test-run-policy",
    pii_types={
        "text": PiiTypeConfig(enabled=True),
        "face": PiiTypeConfig(enabled=False),  # Haar/LBP cascades need a real face image, not synthetic text video
        "audio": PiiTypeConfig(enabled=False),  # faster-whisper model download unavailable in this sandbox
    },
    agreement_threshold=2,
    retry=RetryConfig(max_attempts=3),
)


def _make_text_video(path: str, text: str = "SSN 123-45-6789 on file") -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=white:s=320x240:d=2",
            "-vf", f"drawtext=text='{text}':fontcolor=black:fontsize=20:x=10:y=100",
            "-r", "4", path,
        ],
        capture_output=True, check=True,
    )


def test_run_redacts_burned_in_text_and_resolves_clean(tmp_path):
    source = str(tmp_path / "source.mp4")
    _make_text_video(source)
    output = str(tmp_path / "output.mp4")

    report = Orchestrator(_POLICY, sample_fps=2.0).run(source, output)

    assert os.path.exists(output)
    assert os.path.getsize(output) > 0
    assert all(s.pii_type == "text" for s in report.manifest.spans)
    # The closed loop should converge to a clean redaction within
    # max_attempts - it never withholds output, and the *last* verification
    # pass should find nothing left, whether that took one attempt or
    # needed the retry escalation to get there (see the _POLICY comment).
    assert report.unresolved is False
    assert len(report.verification_passes) >= 1
    assert report.verification_passes[-1].spans_still_flagged == 0


def test_run_on_clean_video_produces_no_spans_and_resolves(tmp_path):
    source = str(tmp_path / "clean.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=white:s=320x240:d=1", "-r", "2", source],
        capture_output=True, check=True,
    )
    output = str(tmp_path / "output.mp4")

    report = Orchestrator(_POLICY, sample_fps=2.0).run(source, output)

    assert os.path.exists(output)
    assert report.manifest.spans == []
    assert report.unresolved is False


def test_run_preserves_native_frame_rate_in_output(tmp_path):
    source = str(tmp_path / "source.mp4")
    _make_text_video(source)
    output = str(tmp_path / "output.mp4")

    Orchestrator(_POLICY, sample_fps=2.0).run(source, output)

    from redactguard_core.pipeline.ingest import get_frame_rate
    assert get_frame_rate(output) == get_frame_rate(source)


def test_run_with_silent_source_produces_video_with_no_audio_stream(tmp_path):
    source = str(tmp_path / "source.mp4")
    _make_text_video(source)
    output = str(tmp_path / "output.mp4")

    Orchestrator(_POLICY, sample_fps=2.0).run(source, output)

    assert has_audio_stream(output) is False


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
