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


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
