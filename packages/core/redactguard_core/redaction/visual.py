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

from redactguard_core.pipeline.ingest import Frame
from redactguard_core.pipeline.manifest import PiiSpan


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


def expand_bbox_px(
    bbox: tuple[float, float, float, float], margin_px: int, width: int, height: int,
) -> tuple[float, float, float, float]:
    """Grow a normalized (x, y, w, h) bbox outward by `margin_px` real
    pixels on every side, clamped to the frame bounds.

    Used by `apply_visual_redactions` so retry escalation (widening the
    redaction margin per docs/adr/0002/RetryController) actually covers
    more of the frame on each attempt, not just a fixed area.
    """
    x, y, w, h = bbox
    mx, my = margin_px / width, margin_px / height
    nx, ny = max(0.0, x - mx), max(0.0, y - my)
    nw = min(1.0 - nx, w + 2 * mx)
    nh = min(1.0 - ny, h + 2 * my)
    return (nx, ny, nw, nh)


def apply_visual_redactions(
    frames: list[Frame], visual_spans: list[PiiSpan], half_window_s: float, margin_px: int,
) -> list[Frame]:
    """Composite face/text redactions onto a set of frames (typically
    decoded at the source's native frame rate - see docs/adr/0007).

    Detections happen at the much sparser `sample_fps` detection runs at,
    so each span's instant is treated as covering a
    [start - half_window_s, end + half_window_s] window (half a detection
    period on either side, so consecutive samples tile the timeline
    without gaps) - any native frame whose timestamp falls in that window
    for a given span gets redacted with that span's (margin-expanded)
    bbox. Faces are pixelated, everything else (text, and any
    plugin-registered visual PII type) is Gaussian-blurred - both
    reversible-uncertainty redactions, never a crop/delete, so timing
    stays intact for the audio track and any downstream re-mux.
    """
    out: list[Frame] = []
    for frame in frames:
        image = frame.image
        width, height = image.size
        for span in visual_spans:
            if span.bbox is None:
                continue
            if not (span.start_time_s - half_window_s <= frame.timestamp_s <= span.end_time_s + half_window_s):
                continue
            bbox = expand_bbox_px(span.bbox, margin_px, width, height)
            image = pixelate_region(image, bbox) if span.pii_type == "face" else blur_region(image, bbox)
        out.append(Frame(timestamp_s=frame.timestamp_s, image=image))
    return out


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
