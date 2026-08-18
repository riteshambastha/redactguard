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
Visual redaction (blur/pixelation)

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

from PIL import Image, ImageFilter


def pixelate_region(frame: Image.Image, bbox: tuple[float, float, float, float], block_size: int = 12) -> Image.Image:
    """Pixelate the region of `frame` given by a normalized (x, y, w, h)
    bbox. Pure, testable image utility - does not depend on which face/text
    detector produced the bbox.
    """
    x, y, w, h = bbox
    W, H = frame.size
    box = (int(x * W), int(y * H), int((x + w) * W), int((y + h) * H))
    region = frame.crop(box)
    small = region.resize(
        (max(1, region.width // block_size), max(1, region.height // block_size)),
        Image.Resampling.NEAREST,
    )
    pixelated = small.resize(region.size, Image.Resampling.NEAREST)
    out = frame.copy()
    out.paste(pixelated, box)
    return out


def blur_region(frame: Image.Image, bbox: tuple[float, float, float, float], radius: int = 18) -> Image.Image:
    """Gaussian-blur the region of `frame` given by a normalized bbox."""
    x, y, w, h = bbox
    W, H = frame.size
    box = (int(x * W), int(y * H), int((x + w) * W), int((y + h) * H))
    region = frame.crop(box).filter(ImageFilter.GaussianBlur(radius))
    out = frame.copy()
    out.paste(region, box)
    return out


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
