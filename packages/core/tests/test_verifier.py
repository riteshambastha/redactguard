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
Tests for the closed-loop verifier

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from PIL import Image, ImageDraw
from redactguard_core.pipeline.ingest import DecodedMedia, Frame
from redactguard_core.pipeline.policy import PiiTypeConfig, PolicyProfile
from redactguard_core.verification.verifier import Verifier

# Real built-in detectors (text/face/audio) run here, same as production -
# no mocking. This exercises the exact detect+vote path Orchestrator.run()
# points at a redacted draft instead of the original source.

_POLICY = PolicyProfile(
    version=1,
    name="test-verify-policy",
    pii_types={
        "text": PiiTypeConfig(enabled=True),
        "face": PiiTypeConfig(enabled=True),
        "audio": PiiTypeConfig(enabled=True),
    },
    agreement_threshold=1,
)


def _text_frame(text: str) -> Frame:
    image = Image.new("RGB", (500, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 80), text, fill="black")
    return Frame(timestamp_s=0.0, image=image)


def test_verify_flags_pii_still_visible_in_redacted_draft():
    # Simulates a botched redaction attempt: the SSN is still legible.
    media = DecodedMedia(source_file="fake.mp4", frames=[_text_frame("SSN 123-45-6789 on file")])
    spans = Verifier().verify(media, _POLICY, agreement_threshold=1)
    assert len(spans) == 1
    assert spans[0].pii_type == "text"


def test_verify_passes_clean_when_nothing_detected():
    # Simulates a successful redaction: a blank frame, nothing left to find.
    media = DecodedMedia(source_file="fake.mp4", frames=[Frame(timestamp_s=0.0, image=Image.new("RGB", (200, 200), "white"))])
    spans = Verifier().verify(media, _POLICY, agreement_threshold=1)
    assert spans == []


def test_verify_uses_threshold_1_by_default_not_policy_threshold():
    # Even with a policy that normally requires 2-detector agreement, a
    # single lingering detection during verification should still count -
    # that's the whole point of the default differing from policy.agreement_threshold.
    strict_policy = _POLICY.model_copy(update={"agreement_threshold": 2})
    media = DecodedMedia(source_file="fake.mp4", frames=[_text_frame("SSN 123-45-6789 on file")])
    spans = Verifier().verify(media, strict_policy)  # default agreement_threshold=1
    assert len(spans) == 1


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
