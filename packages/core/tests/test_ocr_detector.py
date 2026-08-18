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
Tests for the Tesseract OCR text/PII detector

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from PIL import Image, ImageDraw
from redactguard_core.detectors.text.ocr_detector import TesseractOcrDetector
from redactguard_core.pipeline.ingest import DecodedMedia, Frame


def _text_frame(text: str, timestamp_s: float = 0.0) -> Frame:
    """Render `text` large and crisp enough for Tesseract to read reliably,
    without depending on any system font being installed (draws with
    Pillow's built-in bitmap font, then upscales with nearest-neighbor to
    keep edges sharp).
    """
    small = Image.new("RGB", (400, 60), "white")
    draw = ImageDraw.Draw(small)
    draw.text((5, 5), text, fill="black")
    big = small.resize((small.width * 6, small.height * 6), Image.Resampling.NEAREST)
    return Frame(timestamp_s=timestamp_s, image=big)


def test_detects_ssn_pattern_in_frame():
    # Digits/hyphens round-trip through OCR far more reliably than symbols
    # like "@" at this synthetic-image scale - see the walking-skeleton
    # build notes. Real footage doesn't have this artifact; this test is
    # about proving the detect() -> regex -> DetectionResult wiring, not
    # OCR accuracy itself (that's what benchmarks/ is for, later).
    media = DecodedMedia(source_file="fake.mp4", frames=[_text_frame("SSN 123-45-6789 on file")])
    detector = TesseractOcrDetector()
    results = detector.detect(media)
    assert any(r.metadata.get("pattern") == "ssn" and r.matched_text == "123-45-6789" for r in results)


def test_detects_custom_keyword_in_frame():
    media = DecodedMedia(source_file="fake.mp4", frames=[_text_frame("ACME CONFIDENTIAL")])
    detector = TesseractOcrDetector()
    detector._custom_keywords = ["ACME"]
    results = detector.detect(media)
    assert any(r.metadata.get("pattern", "").startswith("keyword:") for r in results)


def test_no_detections_on_blank_frame():
    blank = Frame(timestamp_s=0.0, image=Image.new("RGB", (200, 50), "white"))
    detector = TesseractOcrDetector()
    assert detector.detect(DecodedMedia(source_file="fake.mp4", frames=[blank])) == []


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
