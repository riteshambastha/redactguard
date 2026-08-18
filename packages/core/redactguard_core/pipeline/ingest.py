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
Input ingestion: file/folder walk and demuxing

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field

from PIL import Image

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


def iter_input_paths(path: str) -> Iterator[str]:
    """Yield video file paths for a single file or a folder/archive (batch
    input is a CLI-level feature per docs/architecture.md).
    """
    if os.path.isfile(path):
        yield path
        return
    for root, _dirs, files in os.walk(path):
        for name in files:
            if os.path.splitext(name)[1].lower() in VIDEO_EXTENSIONS:
                yield os.path.join(root, name)


@dataclass
class Frame:
    """One sampled video frame, decoded to a PIL image."""

    timestamp_s: float
    image: Image.Image


@dataclass
class DecodedMedia:
    """What ingest.py hands to detectors: sampled frames for visual
    detectors (face/text) and an extracted audio file path for the audio
    detector, if the source has an audio stream.
    """

    source_file: str
    frames: list[Frame] = field(default_factory=list)
    audio_path: str | None = None


def has_audio_stream(path: str) -> bool:
    """ffprobe-based check - avoids demuxing audio for silent sources."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=index", "-of", "json", path,
        ],
        capture_output=True, text=True, check=True,
    )
    return bool(json.loads(result.stdout).get("streams"))


def demux(path: str, workdir: str) -> str | None:
    """Extract the audio track of `path` to a 16kHz mono WAV under
    `workdir`, suitable for ASR. Returns None if the source has no audio
    stream at all.
    """
    if not has_audio_stream(path):
        return None
    os.makedirs(workdir, exist_ok=True)
    audio_path = os.path.join(workdir, "audio.wav")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", path, "-vn",
            "-ac", "1", "-ar", "16000", audio_path,
        ],
        capture_output=True, check=True,
    )
    return audio_path


def sample_frames(path: str, workdir: str, fps: float = 1.0) -> list[Frame]:
    """Sample frames from `path` at `fps` frames/second via ffmpeg, decoded
    to PIL images with their timestamp. `workdir` holds the intermediate
    PNGs (caller owns cleanup, e.g. a tempfile.TemporaryDirectory).
    """
    os.makedirs(workdir, exist_ok=True)
    pattern = os.path.join(workdir, "frame_%08d.png")
    subprocess.run(
        ["ffmpeg", "-y", "-i", path, "-vf", f"fps={fps}", "-start_number", "0", pattern],
        capture_output=True, check=True,
    )
    frames: list[Frame] = []
    for name in sorted(os.listdir(workdir)):
        if not name.startswith("frame_"):
            continue
        index = int(name[len("frame_"):-len(".png")])
        timestamp_s = index / fps
        frames.append(Frame(timestamp_s=timestamp_s, image=Image.open(os.path.join(workdir, name)).convert("RGB")))
    return frames


def decode_media(path: str, fps: float = 1.0) -> DecodedMedia:
    """Convenience wrapper used by Orchestrator: sample frames and extract
    audio (if present) for one source file, in one temp workspace.

    NOTE: the temp workdir is intentionally not cleaned up here - frame
    images are loaded into memory (`.convert("RGB")` forces the load), but
    `audio_path` points into `workdir` and must stay alive for the audio
    detector to read it. Cleaning this up properly (e.g. a context manager
    the orchestrator closes after all detectors have run) is a known TODO,
    not an oversight.
    """
    workdir = tempfile.mkdtemp(prefix="redactguard-ingest-")
    frames = sample_frames(path, workdir, fps=fps)
    audio_path = demux(path, workdir)
    return DecodedMedia(source_file=path, frames=frames, audio_path=audio_path)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
