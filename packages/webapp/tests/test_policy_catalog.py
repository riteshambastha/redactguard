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
Tests for bundled demo policy discovery

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from redactguard_webapp.policy_catalog import discover_policies, find_policy


def test_discover_policies_finds_both_bundled_demo_profiles():
    names = {choice.profile.name for choice in discover_policies()}
    assert names == {"demo_fast", "demo_with_audio"}


def test_demo_fast_has_audio_disabled_so_it_stays_offline():
    choice = find_policy_or_fail("demo_fast")
    assert choice.profile.pii_types["audio"].enabled is False
    assert choice.profile.pii_types["face"].enabled is True
    assert choice.profile.pii_types["text"].enabled is True


def test_demo_with_audio_enables_all_three_pii_types():
    choice = find_policy_or_fail("demo_with_audio")
    assert all(cfg.enabled for cfg in choice.profile.pii_types.values())


def test_find_policy_returns_none_for_unknown_name():
    from redactguard_webapp.policy_catalog import POLICIES_DIR

    assert find_policy(POLICIES_DIR, "not-a-real-policy") is None


def find_policy_or_fail(name):
    from redactguard_webapp.policy_catalog import POLICIES_DIR

    choice = find_policy(POLICIES_DIR, name)
    assert choice is not None, f"expected bundled policy {name!r} to exist"
    return choice


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
