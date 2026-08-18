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
Compliance policy profile loading and validation

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import yaml
from pydantic import BaseModel, Field


class PiiTypeConfig(BaseModel):
    enabled: bool = True


class RetryConfig(BaseModel):
    max_attempts: int = 3
    escalation: str = "lower_threshold_and_widen_margin"
    on_unresolved: str = "warn"  # see docs/adr/0002 - human-in-the-loop by design


class PolicyProfile(BaseModel):
    version: int
    name: str
    description: str = ""
    pii_types: dict[str, PiiTypeConfig] = Field(default_factory=dict)
    agreement_threshold: int = 2
    custom_keywords: list[str] = Field(default_factory=list)
    retry: RetryConfig = Field(default_factory=RetryConfig)


def load_policy(path: str) -> PolicyProfile:
    """Load and validate a policy profile YAML (e.g. policies/gdpr_v1.yaml)."""
    with open(path) as f:
        raw = yaml.safe_load(f)
    return PolicyProfile.model_validate(raw)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
