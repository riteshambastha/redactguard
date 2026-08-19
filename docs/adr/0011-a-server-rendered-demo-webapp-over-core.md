<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0011. A server-rendered demo web app over redactguard-core, not a JSON API + SPA

- Status: Accepted
- Author: Ritesh Ambastha

## Context

Everything built so far proves the pipeline works from the inside - real
tests, a real CLI, a real Docker image - but there was no way for someone
to *see* it work without cloning the repo and running a command. A small
web app that lets a person sign up, log in, upload their own video, and
watch ensemble detection and the closed-loop redaction guardrail actually
run against it makes the project's core claims checkable in a browser,
not just readable in a README.

The main design choice was how much surface area that app should be:
a full JSON API behind a separate JS single-page app, or something
simpler.

## Decision

Built `packages/webapp` (`redactguard-webapp`) as a fourth installable
package: a FastAPI app that renders server-side Jinja2 HTML pages
directly, with no separate frontend build step and no JSON API contract
to version. It depends on `redactguard-core` the same way `redactguard-cli`
does - it's a second, equally legitimate consumer of the same
`Orchestrator`, not a special case bolted onto it.

Specific choices, each picked for the same reason - fewest moving parts
that still demonstrate the pipeline honestly:

- **Auth**: plain email + password, hashed with bcrypt, a signed session
  cookie (Starlette's `SessionMiddleware`) after login. No OAuth
  provider, no third-party auth service - consistent with "runs entirely
  offline," and appropriate for what this app actually needs to protect
  (one browsing session's own uploaded videos, not a high-value account).
- **Storage**: a single SQLite file for users and jobs. No Postgres, no
  Redis, no message broker - the whole app runs from one `pip install`
  with nothing else to stand up.
- **Background jobs**: a small `ThreadPoolExecutor`, not Celery.
  `Orchestrator.run()` is synchronous and CPU-bound; running it inside an
  async request handler would block the event loop for the whole job, so
  `POST /upload` hands it to a worker thread and returns immediately. The
  job detail page polls via a plain `<meta http-equiv="refresh">` - no
  websockets, no JS polling loop.
- **Two bundled demo policies** (`redactguard_webapp/policies/`), not a
  reach into the repo's top-level `policies/`: `demo_fast` (face + text,
  fully offline) and `demo_with_audio` (adds Whisper transcription,
  which downloads model weights from Hugging Face Hub on first use).
  Bundling its own copies keeps the package installable and runnable
  standalone, independent of the monorepo layout it happens to live in -
  the same reasoning ADR-0004/0009 applied to plugin discovery.

## Consequences

Every route is tested against the *real* pipeline, not a mocked one:
`packages/webapp/tests/test_upload_flow.py` generates a real ffmpeg clip
with burned-in text PII, uploads it through the actual HTTP layer, waits
for the real background job to finish, and asserts the real detected span
count and a real downloadable redacted file - the same proof-by-actually-
running standard the rest of this project holds itself to.

The tradeoff of the server-rendered approach: no polished, app-like
frontend interactivity (no live progress bar, no drag-and-drop), and job
status pages block-refresh rather than streaming updates. That's an
acceptable tradeoff for what this app is for - proving the pipeline runs,
not delivering a production SaaS UX. `packages/webapp/README.md` says so
explicitly, alongside a plain list of what a demo app doesn't harden
(rate limiting, CSRF tokens, email verification, per-user quotas) - the
same "don't oversell what's actually implemented" standard ADR-0009
applied to the example plugin.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
