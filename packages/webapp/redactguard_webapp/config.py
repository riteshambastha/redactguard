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
Runtime configuration

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import os
import secrets

ALLOWED_UPLOAD_EXTENSIONS = (".mp4", ".mov", ".mkv", ".webm", ".avi")


class Settings:
    """All runtime config in one place, read from environment variables
    with sensible defaults - see the package README's configuration
    table. Passed explicitly to `create_app()` rather than read as a
    process-wide singleton, so tests can construct an isolated instance
    (its own tmp data dir + DB) without env-var monkeypatching races.
    """

    def __init__(
        self,
        data_dir: str | None = None,
        secret_key: str | None = None,
        sample_fps: float | None = None,
        max_upload_mb: int | None = None,
        port: int | None = None,
    ) -> None:
        self.data_dir = data_dir or os.environ.get(
            "REDACTGUARD_WEBAPP_DATA_DIR", os.path.join(os.getcwd(), "redactguard_webapp_data")
        )
        self.uploads_dir = os.path.join(self.data_dir, "uploads")
        self.outputs_dir = os.path.join(self.data_dir, "outputs")
        self.db_path = os.path.join(self.data_dir, "redactguard_webapp.db")
        os.makedirs(self.uploads_dir, exist_ok=True)
        os.makedirs(self.outputs_dir, exist_ok=True)

        # No persisted default: an app restart without this set simply
        # invalidates existing sessions (users have to log in again),
        # which is a reasonable default for a demo app - not a security
        # hole, since it never *weakens* signing, only means keys don't
        # survive a restart unless the operator sets this explicitly.
        self.secret_key = secret_key or os.environ.get("REDACTGUARD_WEBAPP_SECRET_KEY") or secrets.token_hex(32)

        self.sample_fps = sample_fps or float(os.environ.get("REDACTGUARD_WEBAPP_SAMPLE_FPS", "1.0"))
        self.max_upload_mb = max_upload_mb or int(os.environ.get("REDACTGUARD_WEBAPP_MAX_UPLOAD_MB", "200"))
        self.port = port or int(os.environ.get("REDACTGUARD_WEBAPP_PORT", "8000"))


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
