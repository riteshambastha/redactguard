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
Retry escalation policy

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

from dataclasses import dataclass

from redactguard_core.pipeline.policy import RetryConfig


@dataclass
class EscalatedSettings:
    agreement_threshold: int
    blur_margin_px: int
    attempt: int


class RetryController:
    """Implements the escalate-and-retry policy referenced in
    docs/adr/0002-mandatory-verify-then-retry-loop.md: each retry lowers the
    agreement threshold (favor recall) and widens the redaction margin,
    up to `retry.max_attempts`. On exhaustion, the caller (Orchestrator)
    is responsible for emitting the "unresolved" warning rather than
    withholding output - this class only computes the escalation, it does
    not decide pass/fail.
    """

    def __init__(self, retry_config: RetryConfig, base_agreement_threshold: int = 2, base_margin_px: int = 4):
        self.config = retry_config
        self.base_agreement_threshold = base_agreement_threshold
        self.base_margin_px = base_margin_px

    def escalate(self, attempt: int) -> EscalatedSettings:
        if attempt >= self.config.max_attempts:
            raise RuntimeError(
                f"max_attempts ({self.config.max_attempts}) exhausted - "
                "caller must emit output with an 'unresolved' warning (ADR-0002), not raise to the user."
            )
        return EscalatedSettings(
            agreement_threshold=max(1, self.base_agreement_threshold - attempt),
            blur_margin_px=self.base_margin_px * (2 ** (attempt + 1)),
            attempt=attempt + 1,
        )


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
