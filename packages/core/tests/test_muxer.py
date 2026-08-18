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
Tests for video encoding + audio/video remuxing (real ffmpeg subprocess calls)

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

import os

from PIL import Image
from pydub.generators import Sine
from redactguard_core.pipeline.ingest import Frame, get_frame_rate, has_audio_stream
from redactguard_core.redaction.muxer import encode_video_from_frames, mux


def test_encode_video_from_frames_produces_playable_file_at_requested_fps(tmp_path):
    frames = [Frame(timestamp_s=i / 2.0, image=Image.new("RGB", (64, 64), "red")) for i in range(4)]
    out_path = str(tmp_path / "video.mp4")
    encode_video_from_frames(frames, fps=2.0, output_path=out_path)
    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) > 0
    assert get_frame_rate(out_path) == 2.0


def test_encode_video_from_frames_rejects_empty_list(tmp_path):
    try:
        encode_video_from_frames([], fps=1.0, output_path=str(tmp_path / "out.mp4"))
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_mux_without_audio_still_produces_a_valid_silent_video(tmp_path):
    frames = [Frame(timestamp_s=0.0, image=Image.new("RGB", (64, 64), "blue"))]
    video_only = str(tmp_path / "video.mp4")
    encode_video_from_frames(frames, fps=1.0, output_path=video_only)

    out_path = str(tmp_path / "out.mp4")
    mux(video_only, None, out_path)
    assert os.path.exists(out_path)
    assert has_audio_stream(out_path) is False


def test_mux_with_audio_combines_both_streams(tmp_path):
    frames = [Frame(timestamp_s=float(i), image=Image.new("RGB", (64, 64), "green")) for i in range(2)]
    video_only = str(tmp_path / "video.mp4")
    encode_video_from_frames(frames, fps=1.0, output_path=video_only)

    audio_path = str(tmp_path / "audio.wav")
    Sine(440).to_audio_segment(duration=2000).export(audio_path, format="wav")

    out_path = str(tmp_path / "out.mp4")
    mux(video_only, audio_path, out_path)
    assert os.path.exists(out_path)
    assert has_audio_stream(out_path) is True


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
