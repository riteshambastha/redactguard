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
Energy-based voice-activity detector - the second, structural audio detector

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import numpy as np

from redactguard_core.detectors.base import AbstractDetector, DetectionResult
from redactguard_core.detectors.registry import register_detector


def find_speech_intervals(
    normalized_samples: np.ndarray,
    sample_rate: int,
    frame_ms: float = 30.0,
    threshold_dbfs: float = -40.0,
    min_duration_s: float = 0.2,
) -> list[tuple[float, float]]:
    """Pure, model-free energy-based VAD: given mono audio samples already
    normalized to [-1.0, 1.0], return [start_s, end_s) windows where
    short-time RMS energy stays above `threshold_dbfs`, merging contiguous
    above-threshold frames and dropping anything shorter than
    `min_duration_s` (a single loud frame of clothes-rustle or a click,
    not sustained speech/audio).

    Kept separate from EnergyVadDetector.detect() so it's fully testable
    with fabricated arrays - no audio file or pydub object needed, the
    same split used for match_transcript_words() in whisper_detector.py.
    """
    frame_len = max(1, int(sample_rate * frame_ms / 1000.0))
    n_frames = len(normalized_samples) // frame_len
    intervals: list[tuple[float, float]] = []
    current_start: float | None = None
    for i in range(n_frames):
        chunk = normalized_samples[i * frame_len : (i + 1) * frame_len]
        rms = float(np.sqrt(np.mean(np.square(chunk)))) if len(chunk) else 0.0
        dbfs = 20 * np.log10(rms) if rms > 0 else -float("inf")
        t = i * frame_len / sample_rate
        if dbfs >= threshold_dbfs:
            if current_start is None:
                current_start = t
        elif current_start is not None:
            if t - current_start >= min_duration_s:
                intervals.append((current_start, t))
            current_start = None
    if current_start is not None:
        end_t = n_frames * frame_len / sample_rate
        if end_t - current_start >= min_duration_s:
            intervals.append((current_start, end_t))
    return intervals


@register_detector("audio")
class EnergyVadDetector(AbstractDetector):
    """Flags "there is audible speech/sound energy here" via short-time
    RMS energy thresholding - no transcription, no semantic understanding
    of *what* was said, just "is this window not silence".

    This is deliberately the second, algorithmically-independent audio
    detector paired with WhisperAudioDetector: ASR models can hallucinate
    plausible-looking words out of silence, background music, or noise (a
    known Whisper failure mode), and requiring a structurally-independent
    detector to also register real energy at that timestamp is exactly
    the check `agreement_threshold=2` (ADR-0001) exists to enforce - see
    docs/adr/0008. It never sets `matched_text` (it doesn't transcribe
    anything), so a voted PiiSpan's `matched_text` still comes from
    whichever contributor actually transcribed the PII.

    Unlike the Whisper detector, this needs no model download at all, so
    (unlike WhisperAudioDetector.detect()) it's fully verified end-to-end
    in this build environment - see test_energy_vad_detector.py.
    """

    name = "energy-vad"
    pii_type = "audio"

    def detect(self, media) -> list[DetectionResult]:
        if not media.audio_path:
            return []
        from pydub import AudioSegment  # imported lazily, mirrors WhisperAudioDetector's style

        audio = AudioSegment.from_wav(media.audio_path).set_channels(1)
        max_val = float(2 ** (8 * audio.sample_width - 1))
        samples = np.array(audio.get_array_of_samples(), dtype=np.float64) / max_val
        intervals = find_speech_intervals(samples, sample_rate=audio.frame_rate)
        return [
            DetectionResult(
                pii_type=self.pii_type,
                confidence=0.5,  # structural-only signal - never claims to know *what* was said
                start_time_s=start_s,
                end_time_s=end_s,
                detector_name=self.name,
            )
            for start_s, end_s in intervals
        ]


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
