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
Tests for ensemble voting

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from redactguard_core.detectors.base import DetectionResult
from redactguard_core.ensemble.voting import vote


def _result(detector_name, start=0.0, end=1.0, pii_type="face", confidence=0.9):
    return DetectionResult(
        pii_type=pii_type,
        confidence=confidence,
        start_time_s=start,
        end_time_s=end,
        detector_name=detector_name,
    )


def test_agreement_above_threshold_produces_span():
    results = [_result("retinaface"), _result("mtcnn")]
    spans = vote(results, agreement_threshold=2)
    assert len(spans) == 1
    assert spans[0].contributing_detectors == ["mtcnn", "retinaface"]


def test_single_detector_below_threshold_is_dropped():
    results = [_result("retinaface")]
    spans = vote(results, agreement_threshold=2)
    assert spans == []


def test_non_overlapping_detections_stay_separate():
    results = [_result("retinaface", 0.0, 1.0), _result("mtcnn", 5.0, 6.0)]
    spans = vote(results, agreement_threshold=1)
    assert len(spans) == 2


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
