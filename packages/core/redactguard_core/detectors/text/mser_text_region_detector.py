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
MSER-based text-region detector - the second, structural text detector

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import cv2
import numpy as np

from redactguard_core.detectors.base import AbstractDetector, DetectionResult
from redactguard_core.detectors.registry import register_detector


@register_detector("text")
class MserTextRegionDetector(AbstractDetector):
    """Flags "this looks structurally like text" regions via OpenCV's MSER
    (Maximally Stable Extremal Regions) blob detector - no OCR, no
    semantic understanding of *what* the text says, just "is there a
    text-shaped high-contrast blob here".

    This is deliberately the second, algorithmically-independent text
    detector paired with TesseractOcrDetector: OCR engines can hallucinate
    readable-looking words out of noise or visual artifacts (a known
    Tesseract failure mode), and requiring a structurally-independent
    detector to also see *something* at the same place is exactly the
    check `agreement_threshold=2` (ADR-0001) exists to enforce - see
    docs/adr/0008. This detector never sets `matched_text` (it doesn't
    read anything), so a voted PiiSpan's `matched_text` still comes from
    whichever contributor actually read the PII.

    Runs two cleanup passes on the raw MSER output before emitting
    anything, both driven by a real finding (see docs/adr/0008): a first
    version of this detector emitted one box per individual character,
    which (a) flooded dev-policy output with near-duplicate spans and
    (b) rarely shared enough spatial overlap with Tesseract's *word-level*
    OCR bbox to satisfy agreement_threshold=2 on the first pass at all -
    the retry loop (ADR-0002) could still recover, but requiring several
    retries for ordinary text is a worse experience than getting it right
    the first time.

    1. `_non_max_suppress`: MSER inherently returns many nested/near-
       duplicate regions per real blob (a word AND several of its
       individual characters AND their sub-strokes are all independently
       "stable"). Keeps only the largest box per cluster of mutually-
       overlapping regions.
    2. `_merge_horizontally_adjacent`: groups the surviving per-character/
       word boxes that sit on the same line and are close together
       horizontally into one line-level box - approximating "a phrase",
       which is the granularity Tesseract's OCR bbox naturally works at,
       so the two detectors' boxes actually overlap enough to corroborate
       each other on real text.
    """

    name = "opencv-mser-text-region"
    pii_type = "text"

    # A bare MSER pass on real footage can return hundreds of tiny blobs
    # (specular highlights, fabric texture, sensor noise) - these bounds
    # keep only region sizes/shapes plausible for on-screen text (roughly
    # a character, word, or short phrase), not "any high-contrast blob".
    _MIN_AREA_FRACTION = 0.0005
    _MAX_AREA_FRACTION = 0.2
    _MIN_ASPECT = 0.1
    _MAX_ASPECT = 15.0
    _NMS_IOU_THRESHOLD = 0.2
    _MAX_MERGE_GAP_RATIO = 2.0
    _MIN_VERTICAL_OVERLAP_FRACTION = 0.4

    def __init__(self) -> None:
        self._mser = cv2.MSER_create()  # type: ignore[attr-defined]  # present at runtime, missing from cv2's stub

    def _detect_boxes(self, gray: np.ndarray):
        """Thin seam around cv2's MSER region detection, mirroring the
        face detectors' `_detect_boxes` pattern (see HaarFaceDetector) -
        keeps the cv2 C-extension call isolated and monkeypatchable in
        tests without needing a real text-shaped image.
        """
        regions, _ = self._mser.detectRegions(gray)
        return [cv2.boundingRect(region) for region in regions]

    def detect(self, media) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        for frame in media.frames:
            width, height = frame.image.size
            gray = cv2.cvtColor(np.array(frame.image), cv2.COLOR_RGB2GRAY)
            frame_area = float(width * height)

            plausible = []
            for (x, y, w, h) in self._detect_boxes(gray):
                area_fraction = (w * h) / frame_area
                aspect = (w / h) if h else 0.0
                if not (self._MIN_AREA_FRACTION <= area_fraction <= self._MAX_AREA_FRACTION):
                    continue
                if not (self._MIN_ASPECT <= aspect <= self._MAX_ASPECT):
                    continue
                plausible.append((x, y, w, h))

            suppressed = _non_max_suppress(plausible, self._NMS_IOU_THRESHOLD)
            merged = _merge_horizontally_adjacent(
                suppressed, self._MAX_MERGE_GAP_RATIO, self._MIN_VERTICAL_OVERLAP_FRACTION,
            )
            for (x, y, w, h) in merged:
                results.append(
                    DetectionResult(
                        pii_type=self.pii_type,
                        confidence=0.5,  # structural-only signal - never claims to know *what* the text says
                        start_time_s=frame.timestamp_s,
                        end_time_s=frame.timestamp_s,
                        detector_name=self.name,
                        bbox=(x / width, y / height, w / width, h / height),
                    )
                )
        return results


def _box_iou_px(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    """IoU of two (x, y, w, h) boxes in pixel units - scale-invariant, so
    pixel vs. normalized coordinates doesn't matter, but this stays local
    to the detector rather than importing ensemble/voting's normalized
    `_iou` to keep the detectors layer independent of the ensemble layer.
    """
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    intersection = iw * ih
    if intersection <= 0:
        return 0.0
    union = aw * ah + bw * bh - intersection
    return intersection / union if union > 0 else 0.0


def _non_max_suppress(
    boxes: list[tuple[int, int, int, int]], iou_threshold: float,
) -> list[tuple[int, int, int, int]]:
    """Greedy NMS: process boxes largest-first, keep a box only if it
    doesn't sufficiently overlap one already kept. Collapses MSER's
    nested/near-duplicate regions (a word, several of its characters, and
    their sub-strokes are all independently "stable" regions) down to one
    representative box per real cluster - see the class docstring.
    """
    ordered = sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)
    kept: list[tuple[int, int, int, int]] = []
    for box in ordered:
        if not any(_box_iou_px(box, k) >= iou_threshold for k in kept):
            kept.append(box)
    return kept


def _should_merge(
    a: tuple[int, int, int, int], b: tuple[int, int, int, int], max_gap_ratio: float, min_vertical_overlap: float,
) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    vy1, vy2 = max(ay, by), min(ay + ah, by + bh)
    vertical_overlap = max(0, vy2 - vy1)
    if min(ah, bh) <= 0 or vertical_overlap / min(ah, bh) < min_vertical_overlap:
        return False
    horizontal_gap = max(ax, bx) - min(ax + aw, bx + bw)  # negative/zero if already overlapping
    return horizontal_gap <= max_gap_ratio * max(ah, bh)


def _merge_horizontally_adjacent(
    boxes: list[tuple[int, int, int, int]], max_gap_ratio: float, min_vertical_overlap: float,
) -> list[tuple[int, int, int, int]]:
    """Greedily union boxes that sit on roughly the same line (their
    vertical extents overlap by at least `min_vertical_overlap` of the
    shorter box's height) and are horizontally close together (the gap
    between them is at most `max_gap_ratio` times the taller box's
    height - i.e. "about a character-width apart or closer"), collapsing
    per-character/word MSER regions into line/phrase-level boxes.

    Runs repeated passes (bounded, not unbounded) since a single sweep can
    miss transitive merges - e.g. box A merges with B, and the resulting
    wider box now also reaches C, which A alone didn't. Stops as soon as a
    pass produces no further merges, so real footage (a handful of text
    regions per frame, not thousands) converges in one or two passes.
    """
    current = list(boxes)
    for _ in range(10):
        merged_any = False
        result: list[tuple[int, int, int, int]] = []
        for box in current:
            placed = False
            for i, existing in enumerate(result):
                if _should_merge(existing, box, max_gap_ratio, min_vertical_overlap):
                    ex, ey, ew, eh = existing
                    x, y, w, h = box
                    nx, ny = min(ex, x), min(ey, y)
                    nx2, ny2 = max(ex + ew, x + w), max(ey + eh, y + h)
                    result[i] = (nx, ny, nx2 - nx, ny2 - ny)
                    placed = True
                    merged_any = True
                    break
            if not placed:
                result.append(box)
        current = result
        if not merged_any:
            break
    return current


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
