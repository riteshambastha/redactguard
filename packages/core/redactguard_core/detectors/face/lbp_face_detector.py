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
LBP-cascade face detector - the second, independent face detector

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

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "lbpcascade_frontalface_improved.xml")


@register_detector("face")
class LbpFaceDetector(AbstractDetector):
    """OpenCV LBP-cascade (Local Binary Patterns) frontal-face detector.

    This is deliberately the *second* face detector, paired with
    HaarFaceDetector: LBP cascades classify on local texture patterns
    rather than Haar's wavelet-like intensity features, so the two share
    little of their failure surface (lighting, rotation, and scale
    sensitivity differ) - see docs/adr/0008 for why that independence,
    not just having a second detector for its own sake, is what makes
    ensemble voting (ADR-0001) meaningful rather than redundant.
    """

    name = "opencv-lbp-cascade"
    pii_type = "face"

    def __init__(self) -> None:
        self._cascade = cv2.CascadeClassifier(_MODEL_PATH)
        if self._cascade.empty():
            raise RuntimeError(f"Failed to load LBP cascade from {_MODEL_PATH!r}")

    def _detect_boxes(self, gray: np.ndarray):
        """Thin seam around cv2's detectMultiScale - see
        HaarFaceDetector._detect_boxes for why this exists (tests
        monkeypatch this plain method rather than a read-only cv2
        C-extension attribute).
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
                        confidence=0.7,  # LBP cascades don't expose a real score either; see docs/threat_model.md
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
