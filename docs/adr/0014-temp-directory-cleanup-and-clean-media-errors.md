<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0014. Clean up pipeline temp directories, and raise a clean error for unreadable media

- Status: Accepted
- Author: Ritesh Ambastha

## Context

A self-audit of the pipeline (`packages/core/redactguard_core/pipeline/`)
looking for real hardening opportunities, ahead of showing this project off
as production-quality engineering rather than demo-quality, turned up two
related problems:

**Every `Orchestrator.run()`/`scan()` call leaked temp directories.**
`ingest.decode_media()` has called `tempfile.mkdtemp()` since it was
written, with a comment noting cleanup was "a known TODO, not an
oversight" - the frame PNGs are loaded into memory immediately
(`.convert("RGB")` forces the read), but `audio_path` stays a path into
that directory for the audio detector to read later, so the directory
itself couldn't just be deleted before returning. Nobody had gone back
to close the loop. `Orchestrator.run()` compounds this: it also calls
`tempfile.mkdtemp()` directly for the native-fps redaction frames and
the per-attempt scratch dir, and calls `decode_media()` again for
*every* verify pass in the retry loop - so one job with 4 retry attempts
leaks 6 directories, not 1. Checking this sandbox confirmed it wasn't
theoretical: **1,168 leaked `redactguard-*` directories (43MB) had
accumulated in `/tmp` over this session's pipeline runs alone**, on a
box that gets reset between sessions - a real self-hosted deployment
processing videos continuously would fill its disk over days or weeks.

**A corrupted, empty, or audio-only input file produced a raw,
unhelpful error.** `ingest.py`'s ffmpeg/ffprobe calls used
`subprocess.run(..., check=True)`, so any rejected file surfaced as a
bare `subprocess.CalledProcessError` - whose default message is just
"Command '[...]' returned non-zero exit status 1", discarding the
actually-useful explanation ffmpeg had already printed to stderr (e.g.
"moov atom not found", "Output file does not contain any stream").
Worse, nothing above `ingest.py` ever caught it: `redactguard_cli`'s
`run`/`scan` commands had no try/except at all, so a bad upload dumped
a full Python traceback to the terminal. `batch`'s own docstring claims
"one file's retry loop or failure never blocks the rest of the batch",
but the code had no try/except around each file's `Orchestrator.run()`
call either - that claim was false; one bad file in a folder actually
aborted the whole batch.

## Decision

**A `MediaDecodeError(RuntimeError)`** in `ingest.py` is now raised
(instead of letting `CalledProcessError`/a bare `RuntimeError` through)
for every case where ffmpeg/ffprobe reject a file: corrupted input,
zero frames decoded, or (via `get_frame_rate`) no video stream to read
a frame rate from. Its message includes the underlying tool's own
stderr, so "why" is preserved instead of discarded.

**Temp directory ownership is now explicit and enforced.**
`DecodedMedia` gained a `workdir` field so callers know what to remove.
`decode_media()` cleans up its own workdir if it fails before
returning (this took a second pass to get right - see below).
`Orchestrator.scan()`/`run()` each collect every workdir they create or
receive (including one per verify-retry attempt in `run()`'s loop) into
a list and remove all of them in a `finally` block, so cleanup happens
on every exit path: clean finish, retries-exhausted finish, or an
unhandled exception.

**Callers turn `MediaDecodeError` into something clean to look at.**
`redactguard_cli`'s `run`/`scan` commands catch it and re-raise as
`click.ClickException`, which prints `Error: <message>` and exits 1 -
no traceback. `batch` now wraps each file's `Orchestrator.run()` call in
its own try/except, writes a `FAILED` report for that file, and moves
on to the next one - making the docstring's isolation claim actually
true, with a `failed_count` reported alongside `unresolved_count` in the
summary line. `redactguard_webapp.jobs.run_job_sync()` (which already
caught all exceptions to avoid taking down its worker thread - see its
own docstring) now special-cases `MediaDecodeError`: its message is
safe to store as the job's `error_message` and show directly on the job
detail page. Anything else (a genuinely unexpected internal error) gets
`logger.exception()`'d in full to the server log, while the job row
gets a generic "check the server log" message - so an uploader never
sees raw internals for a bug that isn't about their file, but an
operator debugging it still has the full traceback.

## A bug the tests caught while building this

The first version of the `Orchestrator.run()`/`scan()` cleanup only
tracked workdirs *returned* by a successful `decode_media()` call. A
new test - snapshot `/tmp/redactguard-*` before and after a `run()` call
on a corrupted file, assert nothing new is left over - failed: the
initial `decode_media()` call for a corrupted source creates its
workdir via `mkdtemp()`, then raises `MediaDecodeError` from inside
`sample_frames()` *before returning*, so `run()` never receives a
`DecodedMedia` to read `.workdir` off of. The leaked directory was
`decode_media()`'s own, created and abandoned in the same call. Fixed
by having `decode_media()` catch its own failures and `shutil.rmtree`
its workdir before re-raising, rather than relying entirely on the
caller. Left in as an object lesson: the temp-dir leak wasn't fixed by
"the caller cleans up what it's given" alone - the function that
creates a resource has to guarantee that it either hands it off cleanly
or removes it itself, on both of its exit paths.

## Consequences

A long-running self-hosted instance no longer accumulates disk usage
proportional to jobs processed - the failure-path test
(`test_run_leaves_no_temp_directories_behind_even_when_it_raises`)
pins this down for both the success and failure cases, and the CLI/
webapp tests confirm a bad upload now reads as one clear sentence
instead of a stack trace wherever it surfaces.

`decode_media()`'s zero-frames guard (raising `MediaDecodeError` if
`sample_frames` somehow produces no PNGs despite `ffmpeg` exiting 0) is
defense in depth rather than something a real ffmpeg build was
observed doing - every corrupted/empty/audio-only case tested here
already made ffmpeg exit non-zero with a clear stderr message, which
`_run_ffmpeg_tool` catches directly.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
