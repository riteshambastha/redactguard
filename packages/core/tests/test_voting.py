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

import pytest
from redactguard_core.detectors.base import DetectionResult
from redactguard_core.ensemble.voting import _iou, vote


def _result(detector_name, start=0.0, end=1.0, pii_type="face", confidence=0.9, bbox=None):
    return DetectionResult(
        pii_type=pii_type,
        confidence=confidence,
        start_time_s=start,
        end_time_s=end,
        detector_name=detector_name,
        bbox=bbox,
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


def test_iou_of_identical_boxes_is_one():
    box = (0.1, 0.1, 0.2, 0.2)
    assert _iou(box, box) == pytest.approx(1.0)


def test_iou_of_disjoint_boxes_is_zero():
    assert _iou((0.0, 0.0, 0.1, 0.1), (0.5, 0.5, 0.1, 0.1)) == 0.0


def test_temporally_overlapping_but_spatially_disjoint_visual_detections_do_not_agree():
    # Two different faces in the same 1-second sample - same pii_type,
    # fully overlapping in time, but on opposite sides of the frame.
    # Without spatial IoU these would incorrectly "agree" and produce a
    # false-agreement span; see docs/adr/0008.
    left_face = _result("opencv-haar-cascade", 0.0, 1.0, bbox=(0.0, 0.0, 0.1, 0.1))
    right_face = _result("opencv-lbp-cascade", 0.0, 1.0, bbox=(0.9, 0.9, 0.1, 0.1))
    spans = vote([left_face, right_face], agreement_threshold=2)
    assert spans == []


def test_temporally_and_spatially_overlapping_visual_detections_agree_with_union_bbox():
    a = _result("opencv-haar-cascade", 0.0, 1.0, bbox=(0.10, 0.10, 0.20, 0.20))
    b = _result("opencv-lbp-cascade", 0.0, 1.0, bbox=(0.15, 0.15, 0.20, 0.20))
    spans = vote([a, b], agreement_threshold=2)
    assert len(spans) == 1
    # union covers both contributors' boxes, not just one arbitrarily
    assert spans[0].bbox == pytest.approx((0.10, 0.10, 0.25, 0.25))


def test_bboxless_detections_ignore_spatial_check_entirely():
    # Audio has no bbox at all - two detectors overlapping in time should
    # still agree purely on the temporal check, same as before.
    a = _result("faster-whisper", 1.0, 2.0, pii_type="audio")
    b = _result("energy-vad", 1.0, 2.0, pii_type="audio")
    spans = vote([a, b], agreement_threshold=2)
    assert len(spans) == 1
    assert spans[0].bbox is None


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
