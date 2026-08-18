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
Tests for shared PII regex/keyword matching

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from redactguard_core.detectors.common.pii_patterns import (
    find_keyword_matches,
    find_pattern_matches,
)


def test_finds_email():
    matches = find_pattern_matches("Contact: jane.doe@example.com for details")
    assert any(m.label == "email" and m.matched_text == "jane.doe@example.com" for m in matches)


def test_finds_ssn_like():
    matches = find_pattern_matches("SSN: 123-45-6789 on file")
    assert any(m.label == "ssn" and m.matched_text == "123-45-6789" for m in matches)


def test_no_false_positive_on_plain_number():
    matches = find_pattern_matches("Aisle 42, shelf 7")
    assert not any(m.label == "ssn" for m in matches)


def test_keyword_matches_are_case_insensitive():
    matches = find_keyword_matches("Visit ACME Corp headquarters", ["acme corp"])
    assert len(matches) == 1
    assert matches[0].label == "keyword:acme corp"
    assert matches[0].matched_text == "ACME Corp"


def test_empty_keyword_list_matches_nothing():
    assert find_keyword_matches("anything at all", []) == []


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
