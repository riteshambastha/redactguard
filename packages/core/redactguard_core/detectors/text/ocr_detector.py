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
OCR-based text/document/screen/plate PII detector

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import pytesseract

from redactguard_core.detectors.base import AbstractDetector, DetectionResult
from redactguard_core.detectors.common.pii_patterns import (
    find_keyword_matches,
    find_pattern_matches,
)
from redactguard_core.detectors.registry import register_detector


@register_detector("text")
class TesseractOcrDetector(AbstractDetector):
    """Reads on-screen text via Tesseract OCR and flags anything matching a
    built-in PII pattern (email/phone/SSN/credit-card) or a policy's
    custom_keywords - this is the "documents, screens, and license plates
    are all just text" detector from docs/adr/0003 and docs/architecture.md.

    Single detector for now (walking-skeleton phase) - a second,
    independently-implemented OCR/text detector is needed before this PII
    type can participate in ensemble voting per docs/adr/0001; until then,
    use a policy with agreement_threshold=1 (see
    policies/walking_skeleton_dev.yaml).
    """

    name = "tesseract-ocr"
    pii_type = "text"

    def __init__(self) -> None:
        self._custom_keywords: list[str] = []

    def configure(self, policy) -> None:
        self._custom_keywords = list(getattr(policy, "custom_keywords", []) or [])

    def detect(self, media) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        for frame in media.frames:
            width, height = frame.image.size
            text = pytesseract.image_to_string(frame.image)
            if not text.strip():
                continue
            data = pytesseract.image_to_data(frame.image, output_type=pytesseract.Output.DICT)
            all_matches = find_pattern_matches(text) + find_keyword_matches(text, self._custom_keywords)
            for match in all_matches:
                bbox = _bbox_for_match(text, match, data, width, height)
                results.append(
                    DetectionResult(
                        pii_type=self.pii_type,
                        confidence=0.9 if not match.label.startswith("keyword:") else 0.75,
                        start_time_s=frame.timestamp_s,
                        end_time_s=frame.timestamp_s,
                        detector_name=self.name,
                        bbox=bbox,
                        matched_text=match.matched_text,
                        metadata={"pattern": match.label},
                    )
                )
        return results


def _bbox_for_match(full_text: str, match, ocr_data: dict, width: int, height: int) -> tuple[float, float, float, float] | None:
    """Best-effort: find which OCR word(s) the match's matched_text falls
    within and union their pixel boxes, normalized to [0, 1]. Falls back
    to None (whole-frame caller can decide a default margin) if no word
    boundary lines up - matched text spanning a Tesseract word-split
    boundary is a known limitation, see docs/threat_model.md.
    """
    needle = match.matched_text.strip().lower()
    if not needle:
        return None
    n_words = len(ocr_data.get("text", []))
    boxes = []
    for i in range(n_words):
        word = ocr_data["text"][i].strip()
        if not word:
            continue
        if word.lower() in needle or needle in word.lower():
            boxes.append((ocr_data["left"][i], ocr_data["top"][i], ocr_data["width"][i], ocr_data["height"][i]))
    if not boxes:
        return None
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    return (x0 / width, y0 / height, (x1 - x0) / width, (y1 - y0) / height)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
