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
Tests for audio redaction (span-driven muting)

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from pydub import AudioSegment
from pydub.generators import Sine
from redactguard_core.pipeline.manifest import PiiSpan
from redactguard_core.redaction.audio import apply_audio_redactions


def _tone_audio(duration_ms=3000) -> AudioSegment:
    return Sine(440).to_audio_segment(duration=duration_ms)


def _audio_span(start_s, end_s):
    return PiiSpan(
        pii_type="audio", confidence=0.9, start_time_s=start_s, end_time_s=end_s,
        contributing_detectors=["faster-whisper"], matched_text="123-45-6789",
    )


def test_muted_window_is_silent():
    audio = _tone_audio(3000)
    redacted = apply_audio_redactions(audio, [_audio_span(1.0, 2.0)])
    middle = redacted[1200:1800]
    assert middle.dBFS == float("-inf")  # AudioSegment.silent() reports -inf dBFS


def test_outside_window_is_unaffected():
    audio = _tone_audio(3000)
    redacted = apply_audio_redactions(audio, [_audio_span(1.0, 2.0)])
    before = redacted[0:500]
    original_before = audio[0:500]
    assert before.dBFS == original_before.dBFS


def test_no_spans_leaves_audio_unchanged():
    audio = _tone_audio(1000)
    redacted = apply_audio_redactions(audio, [])
    assert redacted.dBFS == audio.dBFS


def test_zero_length_span_is_skipped_without_error():
    audio = _tone_audio(1000)
    redacted = apply_audio_redactions(audio, [_audio_span(0.5, 0.5)])
    assert redacted.dBFS == audio.dBFS


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
