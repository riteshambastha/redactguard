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
Closed-loop redaction verifier

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

from redactguard_core.detectors.registry import run_detectors
from redactguard_core.ensemble.voting import vote
from redactguard_core.pipeline.ingest import DecodedMedia
from redactguard_core.pipeline.manifest import PiiSpan
from redactguard_core.pipeline.policy import PolicyProfile


class Verifier:
    """Re-runs detection + voting on a redacted draft to confirm nothing
    was missed. See docs/adr/0002-mandatory-verify-then-retry-loop.md.

    Deliberately takes an already-decoded `DecodedMedia` rather than a
    file path: decoding the redacted draft is the orchestrator's job (it
    already owns the temp-workspace lifecycle for the original source),
    so this stays a pure, easily-unit-testable detect+vote call with no
    file or subprocess I/O of its own.
    """

    def verify(self, media: DecodedMedia, policy: PolicyProfile, agreement_threshold: int = 1) -> list[PiiSpan]:
        """Detect PII in the (already redacted) `media` and vote.

        `agreement_threshold` defaults to 1, not `policy.agreement_threshold`
        - verification asks "does *any* detector still see PII here", not
        "do detectors agree with each other", since post-redaction any
        single hit is a sign the redaction missed something and warrants
        a retry (ADR-0002). The initial detection pass on the *original*
        media still uses the policy's real ensemble threshold.
        """
        results = run_detectors(media, policy)
        return vote(results, agreement_threshold)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
