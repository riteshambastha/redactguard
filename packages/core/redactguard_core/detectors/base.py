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
Detector interface

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DetectionResult:
    """One raw detection from a single detector, before ensemble voting."""

    pii_type: str
    confidence: float
    start_time_s: float
    end_time_s: float
    detector_name: str
    bbox: tuple[float, float, float, float] | None = None
    matched_text: str | None = None
    metadata: dict = field(default_factory=dict)


class AbstractDetector(ABC):
    """Base class for every detector - built-in or third-party plugin.

    Concrete detectors are registered via
    `redactguard_core.detectors.registry.register_detector`.
    """

    name: str = "unnamed-detector"
    pii_type: str = "unknown"

    @abstractmethod
    def detect(self, media) -> list[DetectionResult]:
        """Run detection over decoded media (frames and/or an audio
        transcript, depending on `pii_type`) and return raw candidate
        detections - voting/aggregation happens later, in `ensemble/voting.py`.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
