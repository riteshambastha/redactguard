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

import os
from collections.abc import Iterator

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


def demux(path: str):
    """Split a video file into its video and audio streams.

    TODO (walking-skeleton phase): implement via ffmpeg/PyAV. Deliberately
    left unimplemented in the scaffolding phase - the I/O library choice
    (PyAV vs. ffmpeg-python) is a walking-skeleton decision, not an
    architecture one.
    """
    raise NotImplementedError("demux() lands in the walking-skeleton phase")


def sample_frames(video_stream, fps: float = 1.0):
    """Sample frames from a video stream at a target rate.

    TODO (walking-skeleton phase): see demux().
    """
    raise NotImplementedError("sample_frames() lands in the walking-skeleton phase")


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
