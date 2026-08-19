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
Shared pytest fixtures for the webapp test suite

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import subprocess

import pytest
from fastapi.testclient import TestClient
from redactguard_webapp.app import create_app
from redactguard_webapp.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=str(tmp_path / "data"), secret_key="test-secret-key")


@pytest.fixture
def client(settings):
    app = create_app(settings)
    return TestClient(app)


@pytest.fixture
def signed_up_client(client):
    """A client that's already signed up and logged in as one user -
    most upload/job tests don't care about signup itself.
    """
    client.post(
        "/signup",
        data={"email": "demo@example.com", "password": "password123", "confirm_password": "password123"},
    )
    return client


@pytest.fixture
def text_pii_clip(tmp_path):
    """A short, real ffmpeg-generated clip with burned-in SSN text - the
    same synthetic-clip pattern used throughout packages/core/tests, so
    a real (not mocked) detect -> redact -> verify pass has something to
    genuinely find. No audio track, so this never touches the
    faster-whisper/Hugging Face download path.
    """
    path = str(tmp_path / "clip.mp4")
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=white:s=320x240:d=2",
            "-vf", "drawtext=text='SSN 123-45-6789 on file':fontcolor=black:fontsize=20:x=10:y=100",
            "-r", "4", path,
        ],
        capture_output=True, check=True,
    )
    return path


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
