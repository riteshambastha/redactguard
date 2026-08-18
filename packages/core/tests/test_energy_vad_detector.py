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
Tests for the energy-based VAD detector (the second, structural audio detector)

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine
from redactguard_core.detectors.audio.energy_vad_detector import (
    EnergyVadDetector,
    find_speech_intervals,
)
from redactguard_core.pipeline.ingest import DecodedMedia


def test_find_speech_intervals_pure_silence_returns_nothing():
    silence = np.zeros(16000)  # 1s at 16kHz
    assert find_speech_intervals(silence, sample_rate=16000) == []


def test_find_speech_intervals_finds_a_loud_window_between_silence():
    sample_rate = 16000
    silence = np.zeros(sample_rate // 2)  # 0.5s
    t = np.arange(sample_rate // 2) / sample_rate
    tone = 0.8 * np.sin(2 * np.pi * 440 * t)  # 0.5s loud tone
    samples = np.concatenate([silence, tone, silence])

    intervals = find_speech_intervals(samples, sample_rate=sample_rate)

    assert len(intervals) == 1
    start_s, end_s = intervals[0]
    assert 0.4 <= start_s <= 0.6
    assert 0.9 <= end_s <= 1.1


def test_find_speech_intervals_drops_intervals_shorter_than_min_duration():
    sample_rate = 16000
    t = np.arange(int(sample_rate * 0.05)) / sample_rate  # 50ms blip
    blip = 0.8 * np.sin(2 * np.pi * 440 * t)
    samples = np.concatenate([np.zeros(sample_rate), blip, np.zeros(sample_rate)])
    assert find_speech_intervals(samples, sample_rate=sample_rate, min_duration_s=0.2) == []


def test_detect_skips_entirely_when_no_audio_track():
    detector = EnergyVadDetector()
    media = DecodedMedia(source_file="fake.mp4", frames=[], audio_path=None)
    assert detector.detect(media) == []


def test_detect_finds_tone_in_a_real_wav_file(tmp_path):
    # Real (unmocked) pydub decode + energy analysis, no model of any kind.
    silence = AudioSegment.silent(duration=500)
    tone = Sine(440).to_audio_segment(duration=1000).apply_gain(0)
    audio = silence + tone + silence
    wav_path = str(tmp_path / "audio.wav")
    audio.export(wav_path, format="wav")

    detector = EnergyVadDetector()
    media = DecodedMedia(source_file="fake.mp4", frames=[], audio_path=wav_path)
    results = detector.detect(media)

    assert len(results) == 1
    r = results[0]
    assert r.pii_type == "audio"
    assert r.detector_name == "energy-vad"
    assert r.matched_text is None
    assert 0.3 <= r.start_time_s <= 0.7
    assert 1.3 <= r.end_time_s <= 1.7


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
