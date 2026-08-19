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
All page routes: signup/login/logout, dashboard, upload, job detail/download

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha

Server-rendered pages rather than a JSON API + JS frontend - see the root
README's "why" for the webapp, and packages/webapp/README.md. Protected
routes check `auth.current_user()` directly and redirect to /login rather
than using a FastAPI dependency that raises, since a redirect (not a 401)
is the right response for a page a browser navigated to directly.
"""

from __future__ import annotations

import os
import re
import uuid

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from redactguard_webapp import auth, jobs
from redactguard_webapp.config import ALLOWED_UPLOAD_EXTENSIONS, Settings
from redactguard_webapp.policy_catalog import (
    POLICIES_DIR,
    discover_policies,
    display_for,
    find_policy,
)

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


def _sanitize_filename(name: str) -> str:
    """Basename only (no directory traversal), then restrict to a safe
    character set - the original name is just for display and building
    the output filename, never used to construct a trusted path on its
    own without also being joined under a per-job UUID directory.
    """
    base = os.path.basename(name or "upload")
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return base or "upload"


def _write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


def build_router(settings: Settings) -> APIRouter:
    router = APIRouter()
    templates = Jinja2Templates(directory=TEMPLATES_DIR)

    def render(request: Request, template: str, **context):
        context.setdefault("user", auth.current_user(request, settings))
        return templates.TemplateResponse(request, template, context)

    def render_upload_form(request: Request, user, error: str | None = None):
        choices = discover_policies()
        return render(
            request,
            "upload.html",
            user=user,
            policies=choices,
            policy_display={choice.profile.name: display_for(choice) for choice in choices},
            error=error,
        )

    @router.get("/")
    def index(request: Request):
        # A signed-in visitor has no use for the marketing page - straight
        # to their dashboard, same as before. An anonymous visitor now
        # gets a real landing page (see docs/adr/0015) instead of being
        # redirected straight to /login with no context on what they're
        # signing in to.
        if auth.current_user(request, settings):
            return RedirectResponse("/dashboard", status_code=303)
        return templates.TemplateResponse(request, "landing.html", {})

    # --- signup / login / logout -------------------------------------

    @router.get("/signup")
    def signup_form(request: Request):
        return render(request, "signup.html")

    @router.post("/signup")
    def signup_submit(
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
        confirm_password: str = Form(...),
    ):
        email = email.strip().lower()
        if len(password) < 8:
            return render(request, "signup.html", error="Password must be at least 8 characters.", email=email)
        if password != confirm_password:
            return render(request, "signup.html", error="Passwords do not match.", email=email)
        user_id = auth.create_user(settings.db_path, email, password)
        if user_id is None:
            return render(request, "signup.html", error="That email is already registered.", email=email)
        request.session["user_id"] = user_id
        return RedirectResponse("/dashboard", status_code=303)

    @router.get("/login")
    def login_form(request: Request):
        return render(request, "login.html")

    @router.post("/login")
    def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
        email = email.strip().lower()
        user = auth.authenticate(settings.db_path, email, password)
        if user is None:
            return render(request, "login.html", error="Incorrect email or password.", email=email)
        request.session["user_id"] = user["id"]
        return RedirectResponse("/dashboard", status_code=303)

    @router.post("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    # --- dashboard / upload --------------------------------------------

    @router.get("/dashboard")
    def dashboard(request: Request):
        user = auth.current_user(request, settings)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        return render(request, "dashboard.html", user=user, jobs=jobs.list_jobs(settings.db_path, user["id"]))

    @router.get("/upload")
    def upload_form(request: Request):
        user = auth.current_user(request, settings)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        return render_upload_form(request, user)

    @router.post("/upload")
    async def upload_submit(request: Request, policy_name: str = Form(...), video: UploadFile | None = None):
        user = auth.current_user(request, settings)
        if user is None:
            return RedirectResponse("/login", status_code=303)

        policy_choice = find_policy(POLICIES_DIR, policy_name)
        if policy_choice is None:
            return render_upload_form(request, user, error="Unknown policy profile.")

        if video is None or not video.filename:
            return render_upload_form(request, user, error="Choose a video file.")

        safe_name = _sanitize_filename(video.filename)
        ext = os.path.splitext(safe_name)[1].lower()
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            return render_upload_form(
                request,
                user,
                error=f"Unsupported file type {ext!r}. Allowed: {', '.join(ALLOWED_UPLOAD_EXTENSIONS)}.",
            )

        contents = await video.read()
        max_bytes = settings.max_upload_mb * 1024 * 1024
        if len(contents) > max_bytes:
            return render_upload_form(
                request,
                user,
                error=f"File is larger than the {settings.max_upload_mb} MB limit.",
            )

        job_uuid = uuid.uuid4().hex[:12]
        job_upload_dir = os.path.join(settings.uploads_dir, job_uuid)
        job_output_dir = os.path.join(settings.outputs_dir, job_uuid)
        os.makedirs(job_upload_dir, exist_ok=True)
        os.makedirs(job_output_dir, exist_ok=True)

        input_path = os.path.join(job_upload_dir, safe_name)
        await run_in_threadpool(_write_bytes, input_path, contents)
        output_path = os.path.join(job_output_dir, f"redacted_{safe_name}")

        job_id = jobs.create_job(
            settings.db_path,
            user_id=user["id"],
            original_filename=safe_name,
            policy_name=policy_choice.profile.name,
            input_path=input_path,
            output_path=output_path,
        )
        jobs.submit_job(settings.db_path, job_id, policy_choice.path, settings.sample_fps)
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    # --- job detail / download -----------------------------------------

    @router.get("/jobs/{job_id}")
    def job_detail(request: Request, job_id: int):
        user = auth.current_user(request, settings)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        job = jobs.get_job(settings.db_path, job_id, user_id=user["id"])
        if job is None:
            return RedirectResponse("/dashboard", status_code=303)
        return render(request, "job_detail.html", user=user, job=job)

    @router.get("/jobs/{job_id}/download")
    def job_download(request: Request, job_id: int):
        user = auth.current_user(request, settings)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        job = jobs.get_job(settings.db_path, job_id, user_id=user["id"])
        if job is None:
            # Doesn't exist, or belongs to someone else - bounce to the
            # dashboard rather than to /jobs/{job_id}, which would just
            # hit the same ownership check there and redirect again. Same
            # response either way a foreign job id and a nonexistent one,
            # so this can't be used to enumerate which job ids exist.
            return RedirectResponse("/dashboard", status_code=303)
        if job["status"] != "done" or not os.path.exists(job["output_path"]):
            return RedirectResponse(f"/jobs/{job_id}", status_code=303)
        return FileResponse(job["output_path"], filename=f"redacted_{job['original_filename']}")

    return router


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
