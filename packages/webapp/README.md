<!-- RedactGuard | Author: Ritesh Ambastha -->

# redactguard-webapp

A small, self-contained FastAPI web application that demonstrates the
[RedactGuard](https://github.com/riteshambastha/redactguard) pipeline
end-to-end: sign up, log in, upload a video, and watch ensemble
detection + the closed-loop verify-then-retry guardrail actually run
against it.

This is a demo/reference application, not a production multi-tenant
service - see [Security notes](#security-notes) below before exposing it
beyond your own machine or LAN.

## Run it

```bash
pip install -e packages/core -e packages/webapp
redactguard-webapp
# -> http://127.0.0.1:8000
```

Or with Docker (see the root README for the general Docker approach):

```bash
docker build -f docker/Dockerfile.webapp -t redactguard:webapp .
docker run --rm -p 8000:8000 -v redactguard_webapp_data:/data redactguard:webapp
```

## What it does

1. **Sign up / log in** - email + password, hashed with bcrypt, a signed
   session cookie afterward. Backed by a single SQLite file, so there's
   nothing else to stand up.
2. **Upload a video** and pick a policy profile:
   - `demo_fast` - face + text detection only, runs fully offline (no
     model download at all).
   - `demo_with_audio` - adds spoken-PII detection via faster-whisper,
     which downloads Whisper model weights from Hugging Face Hub on
     first use, so it needs outbound internet access the first time it
     runs.
3. **Watch it process.** The job runs in a background thread (so the
   web server stays responsive) through the same
   `Orchestrator.run()` closed loop the CLI uses: detect → vote →
   redact → verify → retry-with-escalation → report. The job page
   auto-refreshes and shows a live, timestamped progress log of each
   pipeline stage as it happens - see
   [ADR-0012](../../docs/adr/0012-pipeline-progress-reporting.md) - so a
   multi-minute job on a real video reads as "in progress," not just
   an unchanging "running" label.
4. **See the result.** Span count, whether it resolved cleanly or is
   flagged `unresolved` for human review (RedactGuard never silently
   withholds output - see
   [ADR-0002](../../docs/adr/0002-mandatory-verify-then-retry-loop.md)),
   the full audit report, and a download link for the redacted video.

## Configuration

All via environment variables, all optional:

| Variable | Default | Purpose |
|---|---|---|
| `REDACTGUARD_WEBAPP_DATA_DIR` | `./redactguard_webapp_data` | SQLite DB + uploaded/redacted video storage |
| `REDACTGUARD_WEBAPP_SECRET_KEY` | a fresh random key each process start | Session cookie signing key - set this explicitly if you want sessions to survive a restart |
| `REDACTGUARD_WEBAPP_SAMPLE_FPS` | `1.0` | Detection sample rate passed to `Orchestrator` |
| `REDACTGUARD_WEBAPP_MAX_UPLOAD_MB` | `200` | Rejects uploads larger than this |
| `REDACTGUARD_WEBAPP_PORT` | `8000` | Port `redactguard-webapp` listens on |

## Security notes

This is a demo app, built to show the pipeline working end-to-end
behind real signup/login - it has not been hardened for multi-tenant
production use. In particular: there's no rate limiting on login/signup,
no email verification or password reset flow, no CSRF tokens on forms,
and no per-user storage quota. Treat it as a local/LAN portfolio demo,
not something to expose on the open internet without further hardening.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
