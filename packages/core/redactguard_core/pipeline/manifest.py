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
Redaction manifest data model

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, Field


class PiiSpan(BaseModel):
    """A single candidate PII detection that survived ensemble voting."""

    pii_type: str  # "face" | "text" | "audio" | a plugin-registered type
    confidence: float = Field(ge=0.0, le=1.0)
    start_time_s: float
    end_time_s: float
    bbox: tuple[float, float, float, float] | None = None  # x, y, w, h (normalized), visual PII only
    contributing_detectors: list[str] = Field(default_factory=list)
    matched_text: str | None = None  # for text/audio keyword or regex matches


class RedactionManifest(BaseModel):
    """The `scan` output: every detected PII span for one source file.

    No video is modified when this is produced - see
    docs/adr/0002-mandatory-verify-then-retry-loop.md for how `run` uses it.
    """

    source_file: str
    policy_profile: str
    created_at: datetime
    spans: list[PiiSpan] = Field(default_factory=list)

    def to_json(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def from_json(cls, path: str) -> RedactionManifest:
        with open(path) as f:
            return cls.model_validate(json.load(f))


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
