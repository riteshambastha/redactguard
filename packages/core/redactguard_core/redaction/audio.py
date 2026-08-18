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
Audio redaction (mute/beep)

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

from pydub import AudioSegment
from pydub.generators import Sine

from redactguard_core.pipeline.manifest import PiiSpan


def mute_segment(audio: AudioSegment, start_ms: int, end_ms: int) -> AudioSegment:
    """Silence [start_ms, end_ms) of an audio track. Pure, testable utility -
    does not depend on which ASR/PII matcher produced the span.
    """
    silence = AudioSegment.silent(duration=end_ms - start_ms)
    return audio[:start_ms] + silence + audio[end_ms:]


def beep_segment(audio: AudioSegment, start_ms: int, end_ms: int, freq_hz: int = 1000) -> AudioSegment:
    """Replace [start_ms, end_ms) of an audio track with a tone, at the
    original segment's volume so the beep isn't jarring.
    """
    duration = end_ms - start_ms
    tone = Sine(freq_hz).to_audio_segment(duration=duration).apply_gain(audio[start_ms:end_ms].dBFS)
    return audio[:start_ms] + tone + audio[end_ms:]


def apply_audio_redactions(audio: AudioSegment, audio_spans: list[PiiSpan]) -> AudioSegment:
    """Mute every audio PiiSpan's [start_time_s, end_time_s) window.

    Unlike visual spans, Whisper word timestamps already give a real
    interval (no half-window widening needed - see redaction/visual.py's
    apply_visual_redactions for why that's a visual-only concern). Spans
    are applied in time order so overlapping/adjacent spans from a retry's
    lower agreement threshold don't produce out-of-order slice edits.
    """
    for span in sorted(audio_spans, key=lambda s: s.start_time_s):
        start_ms = int(span.start_time_s * 1000)
        end_ms = int(span.end_time_s * 1000)
        if end_ms <= start_ms:
            continue
        audio = mute_segment(audio, start_ms, end_ms)
    return audio


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
