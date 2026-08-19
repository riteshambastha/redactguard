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
Example third-party detector plugin: skin-tone + local-variance tattoo heuristic

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import cv2
import numpy as np
from redactguard_plugin_sdk import AbstractDetector, DetectionResult, register_detector

# Broad HSV skin-tone band (OpenCV's H range is 0-180, not 0-360) - a
# well-known, crude approximation, not a real skin-detection model.
_SKIN_HSV_LOWER = np.array([0, 30, 60], dtype=np.uint8)
_SKIN_HSV_UPPER = np.array([25, 150, 255], dtype=np.uint8)


@register_detector("tattoo")
class TattooDetector(AbstractDetector):
    """Example third-party plugin detector - deliberately NOT a
    production-quality tattoo detector. Real tattoo detection is a
    genuinely hard CV problem that needs a trained model on real data;
    this exists purely to prove RedactGuard's entry_points-based plugin
    discovery (docs/adr/0004, docs/adr/0009) works end-to-end against a
    real, separately-packaged, pip-installed distribution - not just as
    a design sketch.

    Heuristic: within skin-tone regions (HSV thresholding), flag patches
    of unusually high local pixel variance - plain skin is comparatively
    smooth, while inked patterns introduce local contrast. Same honesty
    standard as RedactGuard's own built-in detectors: this will miss real
    tattoos (faded, monochrome, under clothing, on non-exposed skin) and
    will false-positive on moles, blemishes, shadows, or skin creases.
    Anyone copying this as a starting point for a real plugin should
    treat it as a wiring example, not a detection algorithm to trust.
    """

    name = "example-skin-variance-heuristic"
    pii_type = "tattoo"

    _VARIANCE_THRESHOLD = 300.0
    _MIN_AREA_FRACTION = 0.001
    _BLUR_WINDOW = 17  # must be odd for cv2.GaussianBlur

    def _skin_and_variance_mask(self, bgr: np.ndarray) -> np.ndarray:
        """Thin seam isolating the two cv2 passes (skin-tone threshold,
        local-variance estimate) - kept separate from detect()'s
        contour/bbox bookkeeping so tests can exercise the pure image
        logic directly if needed, mirroring the other detectors'
        `_detect_boxes` pattern.
        """
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        skin_mask = cv2.inRange(hsv, _SKIN_HSV_LOWER, _SKIN_HSV_UPPER)

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        local_variance = cv2.GaussianBlur(laplacian**2, (self._BLUR_WINDOW, self._BLUR_WINDOW), 0)
        high_variance_mask = (local_variance > self._VARIANCE_THRESHOLD).astype(np.uint8) * 255

        return cv2.bitwise_and(skin_mask, high_variance_mask)

    def detect(self, media) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        for frame in media.frames:
            width, height = frame.image.size
            frame_area = float(width * height)
            bgr = cv2.cvtColor(np.array(frame.image), cv2.COLOR_RGB2BGR)
            combined_mask = self._skin_and_variance_mask(bgr)

            contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if (w * h) / frame_area < self._MIN_AREA_FRACTION:
                    continue
                results.append(
                    DetectionResult(
                        pii_type=self.pii_type,
                        confidence=0.4,  # crude heuristic - see class docstring
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
