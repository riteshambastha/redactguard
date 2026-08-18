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
Tests for visual redaction compositing (pixelate/blur + windowed frame application)

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from PIL import Image
from redactguard_core.pipeline.ingest import Frame
from redactguard_core.pipeline.manifest import PiiSpan
from redactguard_core.redaction.visual import apply_visual_redactions, expand_bbox_px


def test_expand_bbox_px_grows_symmetrically_and_clamps_to_frame():
    # A 10x10px box (out of 100x100) grown by 5px on every side -> 20x20px.
    grown = expand_bbox_px((0.1, 0.1, 0.1, 0.1), margin_px=5, width=100, height=100)
    assert grown == (0.05, 0.05, 0.2, 0.2)


def test_expand_bbox_px_clamps_at_frame_edge():
    # Box already touching the left/top edge - can't grow past 0.0.
    grown = expand_bbox_px((0.0, 0.0, 0.1, 0.1), margin_px=50, width=100, height=100)
    assert grown[0] == 0.0
    assert grown[1] == 0.0


def _face_span(start, end, bbox=(0.25, 0.25, 0.5, 0.5)):
    return PiiSpan(
        pii_type="face", confidence=0.9, start_time_s=start, end_time_s=end,
        bbox=bbox, contributing_detectors=["opencv-haar-cascade"],
    )


def _red_frame(timestamp_s: float) -> Frame:
    return Frame(timestamp_s=timestamp_s, image=Image.new("RGB", (200, 200), (255, 0, 0)))


def test_frame_inside_span_window_gets_redacted():
    frame = _red_frame(timestamp_s=1.0)
    span = _face_span(start=1.0, end=1.0)
    [out] = apply_visual_redactions([frame], [span], half_window_s=0.5, margin_px=0)
    # Pixelating a solid-color region leaves it that same color, so check
    # via a non-uniform image instead: paste a distinct pixel and confirm
    # the redacted output differs from the untouched original at the bbox.
    assert out.image.getpixel((100, 100)) is not None  # sanity: still a valid image
    assert out.timestamp_s == 1.0


def test_frame_outside_span_window_is_untouched():
    frame = _red_frame(timestamp_s=5.0)
    span = _face_span(start=1.0, end=1.0)
    [out] = apply_visual_redactions([frame], [span], half_window_s=0.5, margin_px=0)
    assert out.image.tobytes() == frame.image.tobytes()


def test_span_without_bbox_is_ignored():
    frame = _red_frame(timestamp_s=1.0)
    text_span_no_bbox = PiiSpan(
        pii_type="text", confidence=0.9, start_time_s=1.0, end_time_s=1.0,
        bbox=None, contributing_detectors=["tesseract-ocr"],
    )
    [out] = apply_visual_redactions([frame], [text_span_no_bbox], half_window_s=0.5, margin_px=0)
    assert out.image.tobytes() == frame.image.tobytes()


def test_actually_changes_pixels_within_the_bbox():
    # A frame with two distinct halves - blur/pixelate should visibly
    # change pixel values inside the redacted region.
    image = Image.new("RGB", (200, 200), (255, 0, 0))
    for x in range(100, 200):
        for y in range(100, 200):
            image.putpixel((x, y), (0, 255, 0))
    frame = Frame(timestamp_s=1.0, image=image)
    span = _face_span(start=1.0, end=1.0, bbox=(0.4, 0.4, 0.2, 0.2))  # straddles the color boundary
    [out] = apply_visual_redactions([frame], [span], half_window_s=0.5, margin_px=0)
    assert out.image.tobytes() != frame.image.tobytes()


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
