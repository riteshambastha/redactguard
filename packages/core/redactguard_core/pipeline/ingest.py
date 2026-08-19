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
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field

from PIL import Image

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


class MediaDecodeError(RuntimeError):
    """Raised for a source file ffmpeg/ffprobe can't make sense of -
    corrupted, zero-length, truncated, or missing an expected stream
    (e.g. no video track). Callers (the CLI commands, the webapp's
    background job runner) catch this specifically to show the user a
    clean one-line message instead of a raw `subprocess.CalledProcessError`
    or a bare traceback - see docs/adr/0014.
    """


def _run_ffmpeg_tool(command: list[str], *, source_file: str) -> subprocess.CompletedProcess[str]:
    """Runs an ffmpeg/ffprobe command, raising `MediaDecodeError` (with the
    tool's own stderr, which is where ffmpeg explains *why* it rejected a
    file) instead of letting `subprocess.CalledProcessError` - whose
    default message is just "returned non-zero exit status 1" - propagate.
    """
    try:
        return subprocess.run(command, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        detail = f": {stderr}" if stderr else " (no error output captured)"
        raise MediaDecodeError(
            f"{command[0]} could not process {source_file!r} - it may be corrupted, "
            f"empty, or not a valid media file{detail}"
        ) from exc
    except FileNotFoundError as exc:
        raise MediaDecodeError(f"{command[0]} is not installed or not on PATH") from exc


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
    workdir: str | None = None
    """The temp directory `frames`/`audio_path` live under, if this
    `DecodedMedia` was produced by `decode_media()` - `None` when built
    directly (as most detector unit tests do). The owner of a `decode_media()`
    call is responsible for removing this directory once done with it
    (`shutil.rmtree(media.workdir, ignore_errors=True)`) - see
    `Orchestrator.scan()`/`run()` and docs/adr/0014.
    """


def has_audio_stream(path: str) -> bool:
    """ffprobe-based check - avoids demuxing audio for silent sources."""
    result = _run_ffmpeg_tool(
        [
            "ffprobe", "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=index", "-of", "json", path,
        ],
        source_file=path,
    )
    return bool(json.loads(result.stdout).get("streams"))


def get_frame_rate(path: str) -> float:
    """ffprobe-based native frame rate lookup, used by the redaction
    compositor (redaction/muxer.py via the orchestrator) to re-encode the
    redacted output at the source's own frame rate rather than the lower
    `sample_fps` detection runs at - see docs/adr/0007.
    """
    result = _run_ffmpeg_tool(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate", "-of", "json", path,
        ],
        source_file=path,
    )
    streams = json.loads(result.stdout).get("streams")
    if not streams:
        raise MediaDecodeError(
            f"{path!r} has no video stream RedactGuard can redact "
            "(is it an audio-only file, or missing a video track?)"
        )
    num, _, den = streams[0]["r_frame_rate"].partition("/")
    return float(num) / float(den or 1)


def demux(path: str, workdir: str) -> str | None:
    """Extract the audio track of `path` to a 16kHz mono WAV under
    `workdir`, suitable for ASR. Returns None if the source has no audio
    stream at all.
    """
    if not has_audio_stream(path):
        return None
    os.makedirs(workdir, exist_ok=True)
    audio_path = os.path.join(workdir, "audio.wav")
    _run_ffmpeg_tool(
        [
            "ffmpeg", "-y", "-i", path, "-vn",
            "-ac", "1", "-ar", "16000", audio_path,
        ],
        source_file=path,
    )
    return audio_path


def sample_frames(path: str, workdir: str, fps: float = 1.0) -> list[Frame]:
    """Sample frames from `path` at `fps` frames/second via ffmpeg, decoded
    to PIL images with their timestamp. `workdir` holds the intermediate
    PNGs (caller owns cleanup, e.g. a tempfile.TemporaryDirectory).
    """
    os.makedirs(workdir, exist_ok=True)
    pattern = os.path.join(workdir, "frame_%08d.png")
    _run_ffmpeg_tool(
        ["ffmpeg", "-y", "-i", path, "-vf", f"fps={fps}", "-start_number", "0", pattern],
        source_file=path,
    )
    frames: list[Frame] = []
    for name in sorted(os.listdir(workdir)):
        if not name.startswith("frame_"):
            continue
        index = int(name[len("frame_"):-len(".png")])
        timestamp_s = index / fps
        frames.append(Frame(timestamp_s=timestamp_s, image=Image.open(os.path.join(workdir, name)).convert("RGB")))
    if not frames:
        raise MediaDecodeError(
            f"{path!r} decoded successfully but produced zero frames - "
            "it may be zero-length or an unsupported/empty video track"
        )
    return frames


def decode_media(path: str, fps: float = 1.0) -> DecodedMedia:
    """Convenience wrapper used by Orchestrator: sample frames and extract
    audio (if present) for one source file, in one temp workspace.

    The returned `DecodedMedia.workdir` points at that temp workspace -
    the caller (`Orchestrator`) is responsible for removing it once done,
    since `audio_path` (unlike `frames`, which are loaded into memory via
    `.convert("RGB")`) is a path into this directory that detectors read
    directly - see docs/adr/0014.

    On failure (e.g. `sample_frames`/`demux` raising `MediaDecodeError` for
    a corrupted source), this function cleans up the workdir it just
    created before re-raising - the caller never receives a `DecodedMedia`
    to clean up after in that case, so if this function didn't self-clean,
    that tempdir would leak on every rejected file.
    """
    workdir = tempfile.mkdtemp(prefix="redactguard-ingest-")
    try:
        frames = sample_frames(path, workdir, fps=fps)
        audio_path = demux(path, workdir)
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    return DecodedMedia(source_file=path, frames=frames, audio_path=audio_path, workdir=workdir)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
