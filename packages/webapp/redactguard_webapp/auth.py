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
User signup, login, and session lookup

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from starlette.requests import Request

from redactguard_webapp.config import Settings
from redactguard_webapp.db import get_connection
from redactguard_webapp.security import hash_password, verify_password


def create_user(db_path: str, email: str, password: str) -> int | None:
    """Returns the new user's id, or None if that email is already
    registered (the caller re-renders the signup form with an error
    rather than this raising).
    """
    conn = get_connection(db_path)
    try:
        if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            return None
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, hash_password(password), now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def authenticate(db_path: str, email: str, password: str) -> sqlite3.Row | None:
    """Returns the user row on success, None on unknown email or wrong
    password - deliberately the same return value for both, so callers
    can't be tempted to reveal which one was wrong.
    """
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row is None or not verify_password(password, row["password_hash"]):
            return None
        return row
    finally:
        conn.close()


def get_user_by_id(db_path: str, user_id: int) -> sqlite3.Row | None:
    conn = get_connection(db_path)
    try:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()


def current_user(request: Request, settings: Settings) -> sqlite3.Row | None:
    """None if there's no session or it doesn't map to a real user
    (e.g. the user was deleted after the cookie was issued) - callers
    treat either case as "not logged in".
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(settings.db_path, user_id)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
