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
Unit tests for job bookkeeping and the synchronous job runner's failure path

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import pytest
from redactguard_webapp import auth, jobs
from redactguard_webapp.db import init_db


def test_update_job_rejects_unrecognized_columns(settings):
    init_db(settings.db_path)
    user_id = auth.create_user(settings.db_path, "a@example.com", "password123")
    job_id = jobs.create_job(
        settings.db_path, user_id=user_id, original_filename="a.mp4", policy_name="demo_fast",
        input_path="/tmp/a.mp4", output_path="/tmp/a.out.mp4",
    )
    with pytest.raises(ValueError, match="unrecognized column"):
        jobs._update_job(settings.db_path, job_id, user_id=999)  # not a real jobs column - would be a SQL-injection-shaped bug


def test_run_job_sync_records_failure_instead_of_raising(settings, tmp_path):
    init_db(settings.db_path)
    user_id = auth.create_user(settings.db_path, "a@example.com", "password123")
    job_id = jobs.create_job(
        settings.db_path, user_id=user_id, original_filename="a.mp4", policy_name="demo_fast",
        input_path=str(tmp_path / "does-not-exist.mp4"), output_path=str(tmp_path / "out.mp4"),
    )

    # A nonexistent input file makes Orchestrator.run() raise - run_job_sync
    # must catch that and record status="failed", not propagate.
    jobs.run_job_sync(settings.db_path, job_id, policy_path=_demo_fast_policy_path(), sample_fps=1.0)

    job = jobs.get_job(settings.db_path, job_id)
    assert job["status"] == "failed"
    assert job["error_message"]


def _demo_fast_policy_path() -> str:
    from redactguard_webapp.policy_catalog import POLICIES_DIR, find_policy

    return find_policy(POLICIES_DIR, "demo_fast").path


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
