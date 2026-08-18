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
Self-hosted Whisper audio PII detector

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

from dataclasses import dataclass

from redactguard_core.detectors.base import AbstractDetector, DetectionResult
from redactguard_core.detectors.common.pii_patterns import (
    find_keyword_matches,
    find_pattern_matches,
)
from redactguard_core.detectors.registry import register_detector


@dataclass
class WordSpan:
    text: str
    char_start: int
    char_end: int
    start_s: float
    end_s: float


def build_indexed_transcript(words) -> tuple[str, list[WordSpan]]:
    """Concatenate word-level ASR output into one transcript string while
    tracking each word's character range and timestamp - lets us reuse the
    same character-offset regex/keyword matching as the OCR detector
    (detectors/common/pii_patterns.py) and then map matches back to a time
    range, the audio equivalent of the OCR detector's bbox unioning.

    `words` items need only `.word`/`.start`/`.end` attributes (matches
    faster-whisper's Word type) or an equivalent (text, start, end) tuple -
    kept duck-typed so tests don't need a real model.
    """
    parts: list[str] = []
    spans: list[WordSpan] = []
    pos = 0
    for w in words:
        text = w.word if hasattr(w, "word") else w[0]
        start_s = w.start if hasattr(w, "start") else w[1]
        end_s = w.end if hasattr(w, "end") else w[2]
        stripped = text.strip()
        if not stripped:
            continue
        if parts:
            parts.append(" ")
            pos += 1
        char_start = pos
        parts.append(stripped)
        pos += len(stripped)
        spans.append(WordSpan(stripped, char_start, pos, start_s, end_s))
    return "".join(parts), spans


def _time_range_for_match(match_start: int, match_end: int, spans: list[WordSpan]) -> tuple[float, float] | None:
    overlapping = [s for s in spans if s.char_start < match_end and match_start < s.char_end]
    if not overlapping:
        return None
    return min(s.start_s for s in overlapping), max(s.end_s for s in overlapping)


def match_transcript_words(words, custom_keywords: list[str], detector_name: str) -> list[DetectionResult]:
    """Pure, model-free matching step: given already-transcribed
    word-timestamp data, find PII spans and map them to time ranges. This
    is what `detect()` delegates to after running Whisper - kept separate
    so it's testable without downloading/running an actual ASR model.
    """
    text, spans = build_indexed_transcript(words)
    if not text:
        return []
    results: list[DetectionResult] = []
    for match in find_pattern_matches(text) + find_keyword_matches(text, custom_keywords):
        time_range = _time_range_for_match(match.start, match.end, spans)
        if time_range is None:
            continue
        start_s, end_s = time_range
        results.append(
            DetectionResult(
                pii_type="audio",
                confidence=0.9 if not match.label.startswith("keyword:") else 0.75,
                start_time_s=start_s,
                end_time_s=end_s,
                detector_name=detector_name,
                matched_text=match.matched_text,
                metadata={"pattern": match.label},
            )
        )
    return results


@register_detector("audio")
class WhisperAudioDetector(AbstractDetector):
    """Transcribes the audio track with a self-hosted Whisper model
    (faster-whisper, CPU int8 by default) and flags PII the same way the
    OCR detector does for on-screen text - built-in regexes plus policy
    custom_keywords, via `match_transcript_words()`.

    NOTE: this detector's actual transcription step needs the Whisper
    model weights, downloaded from Hugging Face Hub on first use and
    cached thereafter - the walking-skeleton development sandbox this was
    built in could not reach huggingface.co to verify that download live
    (see the build-plan log), so `detect()` itself is unverified end-to-end
    here. `match_transcript_words()` - the actual PII-matching logic - IS
    fully tested against fabricated transcript data; only the
    faster-whisper integration itself needs verifying in an environment
    with normal internet access (e.g. Docker build, or your own machine).

    Single detector for now (walking-skeleton phase) - see
    docs/adr/0001-ensemble-voting-for-detection.md and
    policies/walking_skeleton_dev.yaml for the agreement_threshold=1
    interim setting.
    """

    name = "faster-whisper"
    pii_type = "audio"
    model_size = "base"

    def __init__(self) -> None:
        self._custom_keywords: list[str] = []
        self._model = None

    def configure(self, policy) -> None:
        self._custom_keywords = list(getattr(policy, "custom_keywords", []) or [])

    def _get_model(self):
        if self._model is None:
            from faster_whisper import (
                WhisperModel,  # imported lazily - heavy, and downloads weights
            )

            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        return self._model

    def detect(self, media) -> list[DetectionResult]:
        if not media.audio_path:
            return []
        model = self._get_model()
        segments, _info = model.transcribe(media.audio_path, word_timestamps=True)
        words = [w for segment in segments for w in (segment.words or [])]
        return match_transcript_words(words, self._custom_keywords, self.name)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
