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

from datetime import datetime, timezone

from redactguard_core.detectors.base import DetectionResult
from redactguard_core.detectors.registry import get_detectors
from redactguard_core.ensemble.voting import vote
from redactguard_core.pipeline.ingest import decode_media
from redactguard_core.pipeline.manifest import RedactionManifest
from redactguard_core.pipeline.policy import PolicyProfile
from redactguard_core.pipeline.report import AuditReport
from redactguard_core.verification.retry_controller import RetryController


class Orchestrator:
    """Runs one file through: detect -> vote -> [scan stops here] -> redact
    -> verify -> retry -> report. See docs/architecture.md for the full
    pipeline diagram and docs/adr/ for why each stage exists.
    """

    def __init__(self, policy: PolicyProfile, sample_fps: float = 1.0):
        self.policy = policy
        self.sample_fps = sample_fps
        self.retry_controller = RetryController(policy.retry)

    def scan(self, source_file: str) -> RedactionManifest:
        """Dry-run: decode + detect + vote, no video modified. This is the
        CLI's `redactguard scan` output.
        """
        media = decode_media(source_file, fps=self.sample_fps)
        all_results: list[DetectionResult] = []
        for pii_type, cfg in self.policy.pii_types.items():
            if not cfg.enabled:
                continue
            registered = get_detectors(pii_type, policy=self.policy)
            if not registered:
                raise NotImplementedError(
                    f"No detector implementations registered yet for {pii_type!r} "
                    "- this lands in the walking-skeleton phase."
                )
            for detector in registered:
                all_results.extend(detector.detect(media))
        spans = vote(all_results, self.policy.agreement_threshold)
        return RedactionManifest(
            source_file=source_file,
            policy_profile=self.policy.name,
            created_at=datetime.now(timezone.utc),
            spans=spans,
        )

    def run(self, source_file: str, output_file: str) -> AuditReport:
        """Apply the (possibly human-edited) manifest, verify, retry, and
        report. This is the CLI's `redactguard run`.

        TODO (later phases): wire in redaction/visual.py, redaction/audio.py,
        redaction/muxer.py, and verification/verifier.py once the
        walking-skeleton detectors exist.
        """
        raise NotImplementedError("run() lands once redaction + verification are wired up")


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
