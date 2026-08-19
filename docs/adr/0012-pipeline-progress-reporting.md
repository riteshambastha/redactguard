<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0012. Pipeline stage progress reporting via logging + an optional callback

- Status: Accepted
- Author: Ritesh Ambastha

## Context

`Orchestrator.run()` on a real (non-synthetic-test) video can take
anywhere from seconds to several minutes, depending on length,
resolution, and which detectors are enabled - a minute of video sampled
at 1 fps with face+text detection means dozens of frames each running
two cascade classifiers, OCR, and structural region detection, plus a
full native-frame-rate decode/redact/re-encode pass per retry attempt.

Until now, none of that was visible from the outside. The CLI printed
nothing while `run()` executed, and `redactguard-webapp`'s job detail
page (ADR-0011) only ever showed a static "running" label. A user
watching a real job - this was caught by the maintainer actually
uploading a real (non-synthetic) video to the webapp and finding the
"running" status indistinguishable from stuck - had no way to tell
"almost done" from "hung," and no log output to check either.

## Decision

`Orchestrator` gains an `on_progress: Callable[[str], None] | None`
constructor parameter and a `_report()` helper that both stages call at
each meaningful transition (decode, detect, per-attempt vote/redact/
verify, escalate, exhausted-retries, done). `_report()` always calls
`logger.info()` - so `redactguard scan`/`run`/`batch` show live progress
the moment logging is configured - and additionally calls `on_progress`
if one was given, so a caller that isn't just printing to stdout (like
the webapp) can route the same messages somewhere else entirely.

Two consumers wired up immediately:

- `redactguard_cli.main.cli()` calls `logging.basicConfig(level=INFO,
  format="%(message)s")` unless `--quiet` is passed, so the CLI now
  prints each stage as it happens instead of going silent until the
  command exits.
- `redactguard_webapp.jobs.run_job_sync()` passes an `on_progress` that
  appends each message, timestamped, to the job's new `progress_log`
  column (`db.py` migrates existing databases with an idempotent `ALTER
  TABLE ... ADD COLUMN` check, so this doesn't break anyone's existing
  local `redactguard_webapp.db` or in-flight job rows). The job detail
  page renders `progress_log` in a scrolling `<pre>` that auto-scrolls to
  the latest line, and keeps auto-refreshing (already the case before
  this ADR) while the job is queued or running.

## Consequences

A long-running job now has a real answer to "what's it doing right now" -
both in a terminal (CLI) and in a browser (webapp), sourced from the
exact same `_report()` call sites, so the two can never drift out of
sync with each other or with what the pipeline is actually doing.

The progress log is coarse-grained (pipeline stage transitions, not
per-frame or per-detector detail) - deliberately so, both to keep the
message volume readable on a job detail page and because per-frame
logging on a real video would itself become a performance concern.
Per-detector timing/profiling, if wanted later, belongs in `benchmarks/`
rather than in this user-facing progress log.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
