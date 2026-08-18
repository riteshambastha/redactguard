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
Cross-detector agreement voting

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

from redactguard_core.detectors.base import DetectionResult
from redactguard_core.pipeline.manifest import PiiSpan

DEFAULT_IOU_THRESHOLD = 0.1
"""Deliberately loose: our two visual detectors per type use different
algorithms (e.g. Haar vs LBP cascades, or Tesseract's char-level boxes vs
MSER's region proposals) that rarely produce near-identical boxes even
when both have genuinely found the same real-world region. A strict IoU
(0.5+) would defeat the point of pairing algorithmically-diverse
detectors - see docs/adr/0008.
"""


def _iou(a_bbox: tuple[float, float, float, float], b_bbox: tuple[float, float, float, float]) -> float:
    """Intersection-over-union of two normalized (x, y, w, h) boxes."""
    ax, ay, aw, ah = a_bbox
    bx, by, bw, bh = b_bbox
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    intersection = iw * ih
    if intersection <= 0.0:
        return 0.0
    union = aw * ah + bw * bh - intersection
    return intersection / union if union > 0.0 else 0.0


def _overlaps(a: DetectionResult, b: DetectionResult, iou_threshold: float = DEFAULT_IOU_THRESHOLD) -> bool:
    """Same PII type, overlapping in time, AND - for detections that both
    carry a bbox (i.e. visual PII) - overlapping in space above
    `iou_threshold`. Audio (and any future bbox-less PII type) only ever
    has a time dimension, so it keeps the temporal-only check.

    Without the spatial check, two visual detectors flagging unrelated
    regions of the same frame (e.g. two different faces) would incorrectly
    "agree" purely because both fired in the same 1-second sample -
    exactly the false-agreement bug that would make agreement_threshold=2
    meaningless once a second visual detector exists per type (ADR-0008).

    The temporal check uses `<=`, not a strict `<`: every built-in
    detector reports a single instant per frame (`start_time_s ==
    end_time_s`, the sampled frame's own timestamp), and a strict `<`
    means two zero-length intervals at the *same* instant never register
    as overlapping with each other (`0.0 < 0.0` is False) - which would
    make it impossible for two detectors examining the same frame to ever
    agree, no matter how perfectly their boxes align spatially. This was
    a real bug found by running two real detectors per PII type
    end-to-end for the first time (ADR-0008) - a single-detector ensemble
    never exercised this path. `<=` does mean two genuinely back-to-back
    (but non-overlapping) intervals like [0, 1) and [1, 2) count as
    touching at the boundary instant; that's an acceptable, minor
    over-merge compared to the alternative of point-detections never
    agreeing at all.
    """
    if a.pii_type != b.pii_type:
        return False
    if not (a.start_time_s <= b.end_time_s and b.start_time_s <= a.end_time_s):
        return False
    if a.bbox is not None and b.bbox is not None:
        return _iou(a.bbox, b.bbox) >= iou_threshold
    return True


def _union_bbox(
    bboxes: list[tuple[float, float, float, float]],
) -> tuple[float, float, float, float] | None:
    """Smallest box enclosing every bbox in a voted group.

    Two algorithmically-different detectors (Haar vs LBP, Tesseract's
    char-boxes vs MSER's region proposals) rarely draw identical boxes
    around the same real-world region - taking the union rather than an
    arbitrary single contributor's box means the redaction actually
    covers what either detector saw, at the cost of a slightly larger
    redacted area. Returns None if no contributor had a bbox (audio).
    """
    if not bboxes:
        return None
    x1 = min(b[0] for b in bboxes)
    y1 = min(b[1] for b in bboxes)
    x2 = max(b[0] + b[2] for b in bboxes)
    y2 = max(b[1] + b[3] for b in bboxes)
    return (x1, y1, x2 - x1, y2 - y1)


def vote(results: list[DetectionResult], agreement_threshold: int) -> list[PiiSpan]:
    """Group overlapping detections of the same PII type and keep only
    groups where at least `agreement_threshold` distinct detectors agree.

    See docs/adr/0001-ensemble-voting-for-detection.md for why this exists.
    """
    groups: list[list[DetectionResult]] = []
    for r in results:
        placed = False
        for g in groups:
            if any(_overlaps(r, existing) for existing in g):
                g.append(r)
                placed = True
                break
        if not placed:
            groups.append([r])

    spans: list[PiiSpan] = []
    for g in groups:
        distinct_detectors = {r.detector_name for r in g}
        if len(distinct_detectors) < agreement_threshold:
            continue
        spans.append(
            PiiSpan(
                pii_type=g[0].pii_type,
                confidence=max(r.confidence for r in g),
                start_time_s=min(r.start_time_s for r in g),
                end_time_s=max(r.end_time_s for r in g),
                bbox=_union_bbox([r.bbox for r in g if r.bbox is not None]),
                contributing_detectors=sorted(distinct_detectors),
                matched_text=next((r.matched_text for r in g if r.matched_text), None),
            )
        )
    return spans


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
