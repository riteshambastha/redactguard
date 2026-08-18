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
Tests for ffmpeg-based ingest (frame sampling + audio demux)

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

import subprocess

import pytest
from redactguard_core.pipeline.ingest import decode_media, demux, has_audio_stream, sample_frames


def _make_silent_test_video(path: str, duration_s: int = 2) -> None:
    """A tiny synthetic video with no audio track, generated entirely by
    ffmpeg's testsrc filter - no external assets needed.
    """
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc=duration={duration_s}:size=64x64:rate=2",
            path,
        ],
        capture_output=True, check=True,
    )


def _make_test_video_with_tone(path: str, duration_s: int = 2) -> None:
    """A tiny synthetic video WITH an audio track (a sine tone)."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"testsrc=duration={duration_s}:size=64x64:rate=2",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration_s}",
            "-shortest", path,
        ],
        capture_output=True, check=True,
    )


def test_sample_frames_extracts_expected_count(tmp_path):
    video_path = str(tmp_path / "silent.mp4")
    _make_silent_test_video(video_path, duration_s=2)
    frames = sample_frames(video_path, str(tmp_path / "frames"), fps=1.0)
    assert len(frames) >= 2
    assert frames[0].timestamp_s == pytest.approx(0.0)
    assert frames[0].image.mode == "RGB"


def test_has_audio_stream_false_for_silent_video(tmp_path):
    video_path = str(tmp_path / "silent.mp4")
    _make_silent_test_video(video_path, duration_s=1)
    assert has_audio_stream(video_path) is False


def test_has_audio_stream_true_and_demux_produces_wav(tmp_path):
    video_path = str(tmp_path / "with_tone.mp4")
    _make_test_video_with_tone(video_path, duration_s=1)
    assert has_audio_stream(video_path) is True
    audio_path = demux(video_path, str(tmp_path / "audio_out"))
    assert audio_path is not None
    assert audio_path.endswith(".wav")


def test_demux_returns_none_for_silent_video(tmp_path):
    video_path = str(tmp_path / "silent.mp4")
    _make_silent_test_video(video_path, duration_s=1)
    assert demux(video_path, str(tmp_path / "audio_out")) is None


def test_decode_media_bundles_frames_and_audio(tmp_path):
    video_path = str(tmp_path / "with_tone.mp4")
    _make_test_video_with_tone(video_path, duration_s=1)
    media = decode_media(video_path, fps=1.0)
    assert media.source_file == video_path
    assert len(media.frames) >= 1
    assert media.audio_path is not None


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
