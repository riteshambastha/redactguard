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
Tests for the retry escalation controller

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

import pytest
from redactguard_core.pipeline.policy import RetryConfig
from redactguard_core.verification.retry_controller import RetryController


def test_escalation_widens_margin_and_lowers_threshold():
    controller = RetryController(RetryConfig(max_attempts=3), base_agreement_threshold=2, base_margin_px=4)
    first = controller.escalate(attempt=0)
    second = controller.escalate(attempt=1)
    assert second.blur_margin_px > first.blur_margin_px
    assert second.agreement_threshold <= first.agreement_threshold


def test_exhausted_attempts_raises_for_caller_to_handle():
    controller = RetryController(RetryConfig(max_attempts=1))
    with pytest.raises(RuntimeError):
        controller.escalate(attempt=1)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
