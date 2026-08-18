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
Tests for policy profile loading

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

import textwrap

from redactguard_core.pipeline.policy import load_policy


def test_load_policy(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text(textwrap.dedent("""
        version: 1
        name: test_policy
        pii_types:
          face:
            enabled: true
        agreement_threshold: 2
        custom_keywords: ["Acme Corp"]
        retry:
          max_attempts: 2
          on_unresolved: warn
    """))
    policy = load_policy(str(p))
    assert policy.name == "test_policy"
    assert policy.pii_types["face"].enabled is True
    assert policy.retry.max_attempts == 2
    assert "Acme Corp" in policy.custom_keywords


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
