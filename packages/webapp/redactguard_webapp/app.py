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
FastAPI application factory

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha

`create_app()` takes an optional `Settings` rather than reading a global -
tests construct their own `Settings(data_dir=tmp_path, ...)` so each test
gets an isolated SQLite DB and upload/output directories instead of
sharing real ones (or racing on env-var monkeypatching).
"""

from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from redactguard_webapp.config import Settings
from redactguard_webapp.db import init_db
from redactguard_webapp.routes.pages import build_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    init_db(settings.db_path)

    app = FastAPI(
        title="RedactGuard",
        description="Self-hosted, privacy-preserving video PII redaction - demo web app",
    )
    app.state.settings = settings
    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
    app.include_router(build_router(settings))
    return app


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
