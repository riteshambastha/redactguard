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

from redactguard_core.pipeline.manifest import RedactionManifest


class Verifier:
    """Re-runs detection + voting on a redacted draft to confirm nothing
    was missed. See docs/adr/0002-mandatory-verify-then-retry-loop.md.
    """

    def verify(self, redacted_media_path: str) -> RedactionManifest:
        """TODO (walking-skeleton phase): reuses the same detect+vote path
        as Orchestrator.scan(), pointed at the redacted output instead of
        the original file.
        """
        raise NotImplementedError("verify() lands once detectors exist")


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
