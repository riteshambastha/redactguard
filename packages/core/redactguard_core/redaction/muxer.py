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
Remux redacted video + audio

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from redactguard_core.pipeline.ingest import Frame


def encode_video_from_frames(frames: list[Frame], fps: float, output_path: str) -> None:
    """Encode a sequence of redacted frames back into a video-only file
    (no audio track) at `fps`, via ffmpeg's image2 demuxer.

    `frames` is expected at the source's native frame rate (see
    docs/adr/0007) - the walking-skeleton redaction path decodes at
    native fps specifically so this re-encode doesn't itself downgrade
    playback smoothness versus the source.
    """
    if not frames:
        raise ValueError("no frames to encode - source video had 0 decodable frames")
    workdir = tempfile.mkdtemp(prefix="redactguard-encode-")
    try:
        for i, frame in enumerate(frames):
            frame.image.save(os.path.join(workdir, f"frame_{i:08d}.png"))
        pattern = os.path.join(workdir, "frame_%08d.png")
        subprocess.run(
            [
                "ffmpeg", "-y", "-framerate", str(fps), "-i", pattern,
                "-pix_fmt", "yuv420p", "-c:v", "libx264", output_path,
            ],
            capture_output=True, check=True,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def mux(video_path: str, audio_path: str | None, output_path: str) -> None:
    """Remux a redacted video-only stream with a redacted audio stream
    into one output file via ffmpeg. If the source had no audio track at
    all, `audio_path` is None and the video stream is carried straight
    through (still re-containerized via ffmpeg, not a raw file copy, so
    `output_path`'s container/codec is consistent either way).
    """
    if audio_path is None:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-c:v", "copy", output_path],
            capture_output=True, check=True,
        )
        return
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-shortest", output_path,
        ],
        capture_output=True, check=True,
    )


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
