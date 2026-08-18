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
Tests for the LBP-cascade face detector (the second, independent face detector)

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from PIL import Image
from redactguard_core.detectors.face.lbp_face_detector import LbpFaceDetector
from redactguard_core.pipeline.ingest import DecodedMedia, Frame

# Same rationale as test_face_detector.py: no true-positive test here -
# see that file's module note.


def test_cascade_loads_without_error():
    LbpFaceDetector()  # raises RuntimeError if the vendored XML fails to load


def test_no_false_positive_on_blank_frame():
    blank = Frame(timestamp_s=0.0, image=Image.new("RGB", (200, 200), "white"))
    detector = LbpFaceDetector()
    assert detector.detect(DecodedMedia(source_file="fake.mp4", frames=[blank])) == []


def test_detect_returns_pii_type_face_when_present():
    detector = LbpFaceDetector()
    detector._detect_boxes = lambda gray: [(10, 20, 30, 40)]
    frame = Frame(timestamp_s=1.5, image=Image.new("RGB", (100, 200), "white"))
    results = detector.detect(DecodedMedia(source_file="fake.mp4", frames=[frame]))
    assert len(results) == 1
    r = results[0]
    assert r.pii_type == "face"
    assert r.detector_name == "opencv-lbp-cascade"
    assert r.start_time_s == 1.5
    assert r.bbox == (10 / 100, 20 / 200, 30 / 100, 40 / 200)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
