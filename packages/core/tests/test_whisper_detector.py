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
Tests for the Whisper audio PII detector's transcript-matching logic

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from redactguard_core.detectors.audio.whisper_detector import (
    WhisperAudioDetector,
    build_indexed_transcript,
    match_transcript_words,
)
from redactguard_core.pipeline.ingest import DecodedMedia

# NOTE: these tests exercise match_transcript_words()/build_indexed_transcript()
# directly with fabricated word-timestamp tuples - deliberately NOT calling
# WhisperAudioDetector.detect() with a real audio file, since that needs
# the actual faster-whisper model weights (downloaded from Hugging Face
# Hub on first use). That download couldn't be verified from the sandbox
# this was built in - see the module docstring in whisper_detector.py and
# the build-plan log. The one exception below (audio_path=None) tests a
# real guard clause without needing the model at all.


def _word(text, start, end):
    return (text, start, end)  # (word, start_s, end_s) - the tuple form build_indexed_transcript accepts


def test_build_indexed_transcript_tracks_char_offsets_and_times():
    words = [_word("call", 0.0, 0.3), _word("123-45-6789", 0.3, 1.2), _word("now", 1.2, 1.5)]
    text, spans = build_indexed_transcript(words)
    assert text == "call 123-45-6789 now"
    assert spans[1].text == "123-45-6789"
    assert spans[1].start_s == 0.3
    assert spans[1].end_s == 1.2


def test_match_transcript_words_finds_ssn_with_correct_time_range():
    words = [_word("call", 0.0, 0.3), _word("123-45-6789", 0.3, 1.2), _word("now", 1.2, 1.5)]
    results = match_transcript_words(words, custom_keywords=[], detector_name="faster-whisper")
    assert len(results) == 1
    r = results[0]
    assert r.pii_type == "audio"
    assert r.matched_text == "123-45-6789"
    assert r.start_time_s == 0.3
    assert r.end_time_s == 1.2
    assert r.metadata["pattern"] == "ssn"


def test_match_transcript_words_finds_custom_keyword():
    words = [_word("say", 0.0, 0.2), _word("Acme", 0.2, 0.6), _word("Corp", 0.6, 1.0)]
    results = match_transcript_words(words, custom_keywords=["acme corp"], detector_name="faster-whisper")
    assert len(results) == 1
    assert results[0].metadata["pattern"] == "keyword:acme corp"
    assert results[0].start_time_s == 0.2
    assert results[0].end_time_s == 1.0


def test_match_transcript_words_empty_transcript_returns_nothing():
    assert match_transcript_words([], custom_keywords=["anything"], detector_name="faster-whisper") == []


def test_detect_skips_model_entirely_when_no_audio_track():
    detector = WhisperAudioDetector()
    media = DecodedMedia(source_file="fake.mp4", frames=[], audio_path=None)
    assert detector.detect(media) == []
    assert detector._model is None  # never lazily loaded - no download attempted


def test_defaults_to_cpu_int8_when_no_env_vars_set(monkeypatch):
    monkeypatch.delenv("REDACTGUARD_WHISPER_DEVICE", raising=False)
    monkeypatch.delenv("REDACTGUARD_WHISPER_COMPUTE_TYPE", raising=False)
    detector = WhisperAudioDetector()
    assert detector.device == "cpu"
    assert detector.compute_type == "int8"


def test_device_and_compute_type_are_configurable_via_env_vars(monkeypatch):
    # This is what docker/Dockerfile.gpu (or any GPU host) needs set to
    # actually get GPU acceleration - see docs/adr/0010. Only tests the
    # configuration wiring, not real CUDA inference (unverifiable in this
    # sandbox - see the class docstring).
    monkeypatch.setenv("REDACTGUARD_WHISPER_DEVICE", "cuda")
    monkeypatch.delenv("REDACTGUARD_WHISPER_COMPUTE_TYPE", raising=False)
    detector = WhisperAudioDetector()
    assert detector.device == "cuda"
    assert detector.compute_type == "float16"  # sensible default for GPU, not int8

    monkeypatch.setenv("REDACTGUARD_WHISPER_COMPUTE_TYPE", "int8_float16")
    detector2 = WhisperAudioDetector()
    assert detector2.compute_type == "int8_float16"  # explicit override wins


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
