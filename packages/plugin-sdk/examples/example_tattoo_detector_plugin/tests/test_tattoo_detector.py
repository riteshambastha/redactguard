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
Tests for the example tattoo detector plugin's own heuristic

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

import numpy as np
from example_redactguard_tattoo import TattooDetector
from PIL import Image
from redactguard_core.pipeline.ingest import DecodedMedia, Frame

_SKIN_RGB = (200, 150, 120)
_NON_SKIN_RGB = (20, 20, 220)  # saturated blue - well outside the HSV skin band


def _frame_with_patch(base_rgb, patch_seed=0) -> Frame:
    arr = np.full((200, 200, 3), base_rgb, dtype=np.uint8)
    rng = np.random.default_rng(patch_seed)
    arr[80:120, 80:120] = rng.integers(0, 255, size=(40, 40, 3), dtype=np.uint8)
    return Frame(timestamp_s=0.0, image=Image.fromarray(arr))


def test_plain_skin_tone_frame_has_no_detections():
    plain = Frame(timestamp_s=0.0, image=Image.new("RGB", (200, 200), _SKIN_RGB))
    detector = TattooDetector()
    assert detector.detect(DecodedMedia(source_file="fake.mp4", frames=[plain])) == []


def test_high_variance_patch_on_skin_is_detected():
    frame = _frame_with_patch(_SKIN_RGB)
    detector = TattooDetector()
    results = detector.detect(DecodedMedia(source_file="fake.mp4", frames=[frame]))
    assert len(results) == 1
    r = results[0]
    assert r.pii_type == "tattoo"
    assert r.detector_name == "example-skin-variance-heuristic"
    # bbox roughly covers the injected patch (80-120 out of 200px = 0.4-0.6),
    # widened somewhat by the Gaussian blur in the variance estimate.
    x, y, w, h = r.bbox
    assert 0.25 <= x <= 0.45
    assert 0.25 <= y <= 0.45
    assert (x + w) >= 0.55
    assert (y + h) >= 0.55


def test_high_variance_patch_on_non_skin_background_is_not_detected():
    # Same noisy patch, but the surrounding background isn't skin-toned -
    # the skin-mask gate should suppress it entirely.
    frame = _frame_with_patch(_NON_SKIN_RGB)
    detector = TattooDetector()
    assert detector.detect(DecodedMedia(source_file="fake.mp4", frames=[frame])) == []


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
