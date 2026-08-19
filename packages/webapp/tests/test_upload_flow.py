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
End-to-end tests for the upload -> background job -> download flow

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha

These exercise the *real* pipeline (real ffmpeg clip, real Orchestrator.run(),
a real background thread) rather than mocking the detector/job layer - the
whole point of this app is to prove the pipeline actually runs end-to-end
behind a browser-facing UI, so a test that mocked that part would defeat
the purpose. Uses demo_fast (face+text, no audio) so nothing here needs
network access to download Whisper model weights.
"""

from __future__ import annotations

import time

from redactguard_webapp import auth, jobs
from redactguard_webapp.db import init_db


def _wait_for_terminal_status(client, job_url: str, timeout_s: float = 60.0) -> str:
    """Polls the job detail page like a real browser refreshing would,
    until the job reaches 'done' or 'failed'. Returns the final page body.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = client.get(job_url)
        if 'class="status-done"' in r.text or 'class="status-failed"' in r.text:
            return r.text
        time.sleep(0.5)
    raise AssertionError(f"job at {job_url} did not reach a terminal status within {timeout_s}s")


def test_upload_runs_the_real_pipeline_and_resolves_cleanly(signed_up_client, text_pii_clip):
    with open(text_pii_clip, "rb") as f:
        r = signed_up_client.post(
            "/upload",
            data={"policy_name": "demo_fast"},
            files={"video": ("clip.mp4", f, "video/mp4")},
            follow_redirects=False,
        )
    assert r.status_code == 303
    job_url = r.headers["location"]

    body = _wait_for_terminal_status(signed_up_client, job_url)
    assert 'class="status-done"' in body
    assert "Spans detected: " in body
    # A visible burned-in SSN should be found by the text ensemble.
    assert "Spans detected: 0" not in body
    # See docs/adr/0012 - the job detail page should show a real,
    # timestamped stage-by-stage log, not just the final "done" status.
    assert 'id="progress-log"' in body
    assert "detector ensemble" in body


def test_completed_job_download_serves_a_real_redacted_video_file(signed_up_client, text_pii_clip):
    with open(text_pii_clip, "rb") as f:
        r = signed_up_client.post(
            "/upload", data={"policy_name": "demo_fast"}, files={"video": ("clip.mp4", f, "video/mp4")},
            follow_redirects=False,
        )
    job_url = r.headers["location"]
    _wait_for_terminal_status(signed_up_client, job_url)

    r = signed_up_client.get(job_url + "/download")
    assert r.status_code == 200
    assert len(r.content) > 0
    assert r.headers["content-type"] in ("video/mp4", "application/octet-stream")


def test_dashboard_lists_the_uploaded_job(signed_up_client, text_pii_clip):
    with open(text_pii_clip, "rb") as f:
        signed_up_client.post(
            "/upload", data={"policy_name": "demo_fast"}, files={"video": ("clip.mp4", f, "video/mp4")}
        )
    r = signed_up_client.get("/dashboard")
    assert "clip.mp4" in r.text
    assert "demo_fast" in r.text


def test_upload_rejects_disallowed_file_extension(signed_up_client, tmp_path):
    bogus = tmp_path / "not_a_video.txt"
    bogus.write_text("hello")
    with open(bogus, "rb") as f:
        r = signed_up_client.post(
            "/upload", data={"policy_name": "demo_fast"}, files={"video": ("not_a_video.txt", f, "text/plain")}
        )
    assert "Unsupported file type" in r.text


def test_upload_rejects_unknown_policy_name(signed_up_client, text_pii_clip):
    with open(text_pii_clip, "rb") as f:
        r = signed_up_client.post(
            "/upload", data={"policy_name": "not-a-real-policy"}, files={"video": ("clip.mp4", f, "video/mp4")}
        )
    assert "Unknown policy profile" in r.text


def test_a_user_cannot_view_another_users_job(client, text_pii_clip):
    client.post(
        "/signup", data={"email": "owner@example.com", "password": "password123", "confirm_password": "password123"}
    )
    with open(text_pii_clip, "rb") as f:
        r = client.post(
            "/upload", data={"policy_name": "demo_fast"}, files={"video": ("clip.mp4", f, "video/mp4")},
            follow_redirects=False,
        )
    job_url = r.headers["location"]
    client.post("/logout")

    client.post(
        "/signup",
        data={"email": "someone-else@example.com", "password": "password123", "confirm_password": "password123"},
    )
    # Someone else's job id - should bounce to the dashboard, not leak the job.
    r = client.get(job_url, follow_redirects=False)
    assert r.headers["location"] == "/dashboard"

    r = client.get(job_url + "/download", follow_redirects=False)
    assert r.headers["location"] == "/dashboard"


def test_list_jobs_only_returns_that_users_jobs(settings):
    init_db(settings.db_path)
    user_a = auth.create_user(settings.db_path, "a@example.com", "password123")
    user_b = auth.create_user(settings.db_path, "b@example.com", "password123")

    job_id_a = jobs.create_job(settings.db_path, user_id=user_a, original_filename="a.mp4", policy_name="demo_fast",
                                input_path="/tmp/a.mp4", output_path="/tmp/a.out.mp4")
    jobs.create_job(settings.db_path, user_id=user_b, original_filename="b.mp4", policy_name="demo_fast",
                     input_path="/tmp/b.mp4", output_path="/tmp/b.out.mp4")

    user_a_jobs = jobs.list_jobs(settings.db_path, user_id=user_a)
    assert [row["id"] for row in user_a_jobs] == [job_id_a]


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
