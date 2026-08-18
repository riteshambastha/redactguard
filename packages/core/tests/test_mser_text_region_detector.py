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
Tests for the MSER text-region detector (the second, structural text detector)

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from PIL import Image, ImageDraw
from redactguard_core.detectors.text.mser_text_region_detector import (
    MserTextRegionDetector,
    _merge_horizontally_adjacent,
    _non_max_suppress,
)
from redactguard_core.pipeline.ingest import DecodedMedia, Frame


def test_no_detections_on_blank_frame():
    blank = Frame(timestamp_s=0.0, image=Image.new("RGB", (200, 200), "white"))
    detector = MserTextRegionDetector()
    assert detector.detect(DecodedMedia(source_file="fake.mp4", frames=[blank])) == []


def test_detects_text_shaped_regions_in_a_real_text_image():
    # Real (unmocked) MSER pass over rendered text - this is the whole
    # point of pairing it with Tesseract: no OCR happens here at all.
    image = Image.new("RGB", (500, 200), "white")
    ImageDraw.Draw(image).text((20, 80), "SSN 123-45-6789 on file", fill="black")
    frame = Frame(timestamp_s=0.0, image=image)
    detector = MserTextRegionDetector()
    results = detector.detect(DecodedMedia(source_file="fake.mp4", frames=[frame]))
    assert len(results) > 0
    # MSER inherently returns many nested regions per glyph/word - NMS
    # should collapse that down to a manageable handful, not hundreds.
    assert len(results) < 30
    for r in results:
        assert r.pii_type == "text"
        assert r.detector_name == "opencv-mser-text-region"
        assert r.matched_text is None  # structural only - never reads the text


def test_non_max_suppress_keeps_only_the_largest_of_overlapping_boxes():
    boxes = [
        (0, 0, 10, 10),   # a tiny sub-region...
        (0, 0, 20, 20),   # ...nested inside this larger one
        (100, 100, 5, 5),  # unrelated, distant region - kept independently
    ]
    kept = _non_max_suppress(boxes, iou_threshold=0.2)
    assert (0, 0, 20, 20) in kept
    assert (0, 0, 10, 10) not in kept
    assert (100, 100, 5, 5) in kept
    assert len(kept) == 2


def test_non_max_suppress_keeps_disjoint_boxes_separately():
    boxes = [(0, 0, 10, 10), (50, 50, 10, 10)]
    assert sorted(_non_max_suppress(boxes, iou_threshold=0.2)) == sorted(boxes)


def test_merge_horizontally_adjacent_joins_same_line_close_boxes():
    # Three "characters" on the same line, close together - like OCR's
    # word-level bbox, this should collapse to one wide box.
    boxes = [(0, 0, 8, 10), (10, 1, 8, 10), (20, 0, 8, 10)]
    merged = _merge_horizontally_adjacent(boxes, max_gap_ratio=2.0, min_vertical_overlap=0.4)
    assert len(merged) == 1
    x, _y, w, _h = merged[0]
    assert x == 0
    assert x + w == 28


def test_merge_horizontally_adjacent_leaves_far_apart_boxes_separate():
    boxes = [(0, 0, 8, 10), (500, 0, 8, 10)]
    merged = _merge_horizontally_adjacent(boxes, max_gap_ratio=2.0, min_vertical_overlap=0.4)
    assert sorted(merged) == sorted(boxes)


def test_merge_horizontally_adjacent_leaves_different_lines_separate():
    # Close horizontally, but on different lines (no vertical overlap).
    boxes = [(0, 0, 8, 10), (10, 100, 8, 10)]
    merged = _merge_horizontally_adjacent(boxes, max_gap_ratio=2.0, min_vertical_overlap=0.4)
    assert sorted(merged) == sorted(boxes)


def test_merge_horizontally_adjacent_transitive_chain():
    # A merges with B, and the resulting wider box now also reaches C -
    # a single non-transitive pass would miss this.
    boxes = [(0, 0, 8, 10), (12, 0, 8, 10), (24, 0, 8, 10)]
    merged = _merge_horizontally_adjacent(boxes, max_gap_ratio=1.1, min_vertical_overlap=0.4)
    assert len(merged) == 1


def test_area_and_aspect_filters_via_mocked_boxes():
    detector = MserTextRegionDetector()
    detector._detect_boxes = lambda gray: [
        (0, 0, 20, 10),      # plausible text-shaped box - kept
        (0, 0, 1, 1),        # far too small - dropped
        (0, 0, 199, 199),    # far too large - dropped
        (0, 0, 199, 1),      # extreme aspect ratio - dropped
    ]
    frame = Frame(timestamp_s=0.0, image=Image.new("RGB", (200, 200), "white"))
    results = detector.detect(DecodedMedia(source_file="fake.mp4", frames=[frame]))
    assert len(results) == 1
    assert results[0].bbox == (0.0, 0.0, 20 / 200, 10 / 200)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
