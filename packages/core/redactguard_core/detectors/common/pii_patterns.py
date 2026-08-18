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
Shared PII regex/keyword matching

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Deliberately simple, high-precision-leaning patterns for the
# walking-skeleton phase - see docs/threat_model.md: these will miss
# unusual formats and are not a substitute for a real PII/NER model
# (Presidio lands with the audio detector).
PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"(?<!\d)(\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"),
    "ssn": re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
    "credit_card": re.compile(r"(?<!\d)(?:\d{4}[\s-]?){3}\d{4}(?!\d)"),
}


@dataclass
class PatternMatch:
    label: str  # pattern name (e.g. "email") or "keyword:<term>"
    matched_text: str
    start: int
    end: int


def find_pattern_matches(text: str) -> list[PatternMatch]:
    """Run every built-in PII regex against `text`."""
    matches: list[PatternMatch] = []
    for label, pattern in PATTERNS.items():
        for m in pattern.finditer(text):
            matches.append(PatternMatch(label=label, matched_text=m.group(0), start=m.start(), end=m.end()))
    return matches


def find_keyword_matches(text: str, keywords: list[str]) -> list[PatternMatch]:
    """Case-insensitive, literal substring matching against a policy's
    custom_keywords. See docs/architecture.md - this is intentionally not
    semantic matching (no paraphrase/synonym detection); documented as a
    known limitation in docs/threat_model.md.
    """
    matches: list[PatternMatch] = []
    lowered = text.lower()
    for kw in keywords:
        kw_lower = kw.lower()
        if not kw_lower:
            continue
        start = 0
        while True:
            idx = lowered.find(kw_lower, start)
            if idx == -1:
                break
            matches.append(PatternMatch(label=f"keyword:{kw}", matched_text=text[idx:idx + len(kw)], start=idx, end=idx + len(kw)))
            start = idx + len(kw_lower)
    return matches


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
