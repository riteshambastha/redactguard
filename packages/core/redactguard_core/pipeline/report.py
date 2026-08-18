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
Per-run and per-batch audit report

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from redactguard_core.pipeline.manifest import RedactionManifest


class VerificationPass(BaseModel):
    attempt: int
    spans_still_flagged: int
    escalated: bool


class AuditReport(BaseModel):
    """Manifest + verification history + final status for one file.

    `unresolved=True` means retry.max_attempts was exhausted with PII still
    flagged; per ADR-0002 the output is still emitted, with `warnings` set.
    """

    manifest: RedactionManifest
    verification_passes: list[VerificationPass] = Field(default_factory=list)
    unresolved: bool = False
    warnings: list[str] = Field(default_factory=list)

    def render_markdown(self) -> str:
        lines = [f"# Audit report - {self.manifest.source_file}", ""]
        if self.unresolved:
            lines += ["**UNRESOLVED - human review required.**", ""]
            lines += [f"- {w}" for w in self.warnings]
        lines.append(f"\nSpans detected: {len(self.manifest.spans)}")
        lines.append(f"Verification passes: {len(self.verification_passes)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
