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
Job records and background execution of the RedactGuard pipeline

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha

Orchestrator.run() is synchronous and CPU-bound (OpenCV cascades, OCR,
optionally Whisper) - running it directly inside an async FastAPI request
handler would block the whole event loop for the duration of one user's
job. Instead, POST /upload returns immediately after handing the job to
a small thread pool here; the job detail page polls status via a normal
page refresh. No Celery/Redis/message broker - a demo app processing one
user's video at a time doesn't need one, and pulling one in would work
against the "runs entirely offline with nothing else to stand up" pitch.
"""

from __future__ import annotations

import sqlite3
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from redactguard_core.pipeline.orchestrator import Orchestrator
from redactguard_core.pipeline.policy import load_policy

from redactguard_webapp.db import get_connection

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="redactguard-job")


def create_job(
    db_path: str,
    user_id: int,
    original_filename: str,
    policy_name: str,
    input_path: str,
    output_path: str,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO jobs "
            "(user_id, original_filename, policy_name, status, input_path, output_path, created_at, updated_at) "
            "VALUES (?, ?, ?, 'queued', ?, ?, ?, ?)",
            (user_id, original_filename, policy_name, input_path, output_path, now, now),
        )
        conn.commit()
        assert cur.lastrowid is not None  # always set after a successful INSERT
        return cur.lastrowid
    finally:
        conn.close()


def get_job(db_path: str, job_id: int, user_id: int | None = None) -> sqlite3.Row | None:
    """If `user_id` is given, only returns the job when it belongs to
    that user - callers use this for the ownership check on job-detail
    and download routes, so one user can never view or download another
    user's video by guessing a job id.
    """
    conn = get_connection(db_path)
    try:
        if user_id is not None:
            return conn.execute("SELECT * FROM jobs WHERE id = ? AND user_id = ?", (job_id, user_id)).fetchone()
        return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    finally:
        conn.close()


def list_jobs(db_path: str, user_id: int) -> list[sqlite3.Row]:
    conn = get_connection(db_path)
    try:
        return conn.execute("SELECT * FROM jobs WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    finally:
        conn.close()


def submit_job(db_path: str, job_id: int, policy_path: str, sample_fps: float) -> None:
    """Hands the job to the background thread pool and returns
    immediately. `run_job_sync` (below) is exposed separately so tests
    can call it directly and wait for the result deterministically,
    instead of racing a background thread.
    """
    _EXECUTOR.submit(run_job_sync, db_path, job_id, policy_path, sample_fps)


def run_job_sync(db_path: str, job_id: int, policy_path: str, sample_fps: float) -> None:
    """Actually run one job to completion: detect -> redact -> verify ->
    retry -> report, via the same `Orchestrator` the CLI uses. Never
    raises - any exception is caught and recorded as a failed job, so a
    bad upload or a detector crash can't take down the worker thread
    silently.

    Passes `on_progress=` so every pipeline-stage message Orchestrator
    reports (see docs/adr/0012) is appended to the job's `progress_log`
    as it happens - before this, a multi-minute job just showed
    "running" on the job detail page with no way to tell it apart from
    being stuck.
    """
    _update_job(db_path, job_id, status="running")
    row = get_job(db_path, job_id)
    if row is None:
        return
    try:
        policy = load_policy(policy_path)
        orchestrator = Orchestrator(
            policy, sample_fps=sample_fps, on_progress=lambda message: _append_progress(db_path, job_id, message)
        )
        report = orchestrator.run(row["input_path"], row["output_path"])
        _update_job(
            db_path,
            job_id,
            status="done",
            spans_detected=len(report.manifest.spans),
            unresolved=int(report.unresolved),
            report_markdown=report.render_markdown(),
        )
    except Exception:  # noqa: BLE001 - intentionally blind: any detector/orchestrator failure
        # must land as a failed job row, never crash the worker thread or take
        # down other users' jobs sharing the same ThreadPoolExecutor.
        _append_progress(db_path, job_id, "Job failed - see error details below")
        _update_job(db_path, job_id, status="failed", error_message=traceback.format_exc(limit=5))


def _append_progress(db_path: str, job_id: int, message: str) -> None:
    """Appends one timestamped line to the job's progress_log - a plain
    UPDATE ... SET progress_log = progress_log || ? rather than routing
    through `_update_job`, since this needs to append to the existing
    value, not replace it.
    """
    line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}\n"
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE jobs SET progress_log = progress_log || ?, updated_at = ? WHERE id = ?",
            (line, now, job_id),
        )
        conn.commit()
    finally:
        conn.close()


_ALLOWED_UPDATE_FIELDS = {"status", "spans_detected", "unresolved", "report_markdown", "error_message", "updated_at"}


def _update_job(db_path: str, job_id: int, **fields) -> None:
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    unknown = set(fields) - _ALLOWED_UPDATE_FIELDS
    if unknown:
        # Column names can never come from user input in this module's
        # current callers, but this keeps it that way even if a future
        # caller passes a **kwargs value through from a request - the
        # column list is a fixed allowlist, not string-built from input.
        raise ValueError(f"Refusing to build a SQL UPDATE with unrecognized column(s): {unknown}")
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    conn = get_connection(db_path)
    try:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", (*fields.values(), job_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
