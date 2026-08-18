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


def _overlaps(a: DetectionResult, b: DetectionResult) -> bool:
    """Temporal overlap check; visual detections additionally need spatial
    overlap once bbox-based IoU is implemented (walking-skeleton phase -
    this is a deliberately simple placeholder for the time dimension only).
    """
    return a.pii_type == b.pii_type and a.start_time_s < b.end_time_s and b.start_time_s < a.end_time_s


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
                bbox=g[0].bbox,
                contributing_detectors=sorted(distinct_detectors),
                matched_text=next((r.matched_text for r in g if r.matched_text), None),
            )
        )
    return spans


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
