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
Tests for schema migration on an existing database

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha

See docs/adr/0012: progress_log was added to the jobs table after the
initial schema, so init_db() must be able to run against a database that
predates that column (e.g. someone's existing local
redactguard_webapp.db with jobs already in it) without losing data or
raising "no such column."
"""

from __future__ import annotations

import sqlite3

from redactguard_webapp.db import get_connection, init_db

_PRE_MIGRATION_SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    original_filename TEXT NOT NULL,
    policy_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    input_path TEXT NOT NULL,
    output_path TEXT NOT NULL,
    spans_detected INTEGER,
    unresolved INTEGER,
    report_markdown TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def test_init_db_migrates_an_existing_pre_progress_log_database(tmp_path):
    db_path = str(tmp_path / "old.db")

    # Simulate a database created before progress_log existed, with a
    # real job row already in it - the exact situation a user with an
    # in-flight job hits when they update to this version.
    conn = sqlite3.connect(db_path)
    conn.executescript(_PRE_MIGRATION_SCHEMA)
    conn.execute(
        "INSERT INTO users (email, password_hash, created_at) VALUES ('a@example.com', 'hash', '2026-01-01')"
    )
    conn.execute(
        "INSERT INTO jobs (user_id, original_filename, policy_name, status, input_path, output_path, "
        "created_at, updated_at) VALUES (1, 'a.mp4', 'demo_fast', 'running', '/tmp/a.mp4', '/tmp/out.mp4', "
        "'2026-01-01', '2026-01-01')"
    )
    conn.commit()
    conn.close()

    init_db(db_path)

    conn = get_connection(db_path)
    try:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
        assert "progress_log" in columns

        row = conn.execute("SELECT * FROM jobs WHERE id = 1").fetchone()
        assert row["original_filename"] == "a.mp4"  # pre-existing data survived the migration
        assert row["progress_log"] == ""  # backfilled default for a pre-existing row
    finally:
        conn.close()


def test_init_db_is_idempotent_on_an_already_migrated_database(tmp_path):
    db_path = str(tmp_path / "new.db")
    init_db(db_path)
    init_db(db_path)  # must not raise "duplicate column name" on the second call

    conn = get_connection(db_path)
    try:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
        assert "progress_log" in columns
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
