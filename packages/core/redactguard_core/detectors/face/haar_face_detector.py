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
Haar-cascade face detector

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import os

import cv2
import numpy as np

from redactguard_core.detectors.base import AbstractDetector, DetectionResult
from redactguard_core.detectors.registry import register_detector

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "haarcascade_frontalface_default.xml")


@register_detector("face")
class HaarFaceDetector(AbstractDetector):
    """OpenCV Haar-cascade frontal-face detector.

    Single detector for now (walking-skeleton phase) - see
    docs/adr/0006-vendor-haar-cascade.md for why Haar cascade rather than a
    DNN-based detector (e.g. mediapipe) for this first slice, and
    policies/walking_skeleton_dev.yaml for the agreement_threshold=1
    interim setting until a second, independent face detector exists for
    real ensemble voting (docs/adr/0001).
    """

    name = "opencv-haar-cascade"
    pii_type = "face"

    def __init__(self) -> None:
        self._cascade = cv2.CascadeClassifier(_MODEL_PATH)
        if self._cascade.empty():
            raise RuntimeError(f"Failed to load Haar cascade from {_MODEL_PATH!r}")

    def _detect_boxes(self, gray: np.ndarray):
        """Thin seam around cv2's detectMultiScale.

        Split out purely so tests can monkeypatch a plain Python method
        instead of an attribute on the cv2.CascadeClassifier C-extension
        object, which is read-only and can't be monkeypatched directly.
        """
        return self._cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24),
        )

    def detect(self, media) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        for frame in media.frames:
            width, height = frame.image.size
            gray = cv2.cvtColor(np.array(frame.image), cv2.COLOR_RGB2GRAY)
            boxes = self._detect_boxes(gray)
            for (x, y, w, h) in boxes:
                results.append(
                    DetectionResult(
                        pii_type=self.pii_type,
                        confidence=0.75,  # Haar cascades don't expose a real score; see docs/threat_model.md
                        start_time_s=frame.timestamp_s,
                        end_time_s=frame.timestamp_s,
                        detector_name=self.name,
                        bbox=(x / width, y / height, w / width, h / height),
                    )
                )
        return results


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
