<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0016. CI never installed tesseract-ocr, so every run has been failing

- Status: Accepted
- Author: Ritesh Ambastha

## Context

The repository's `ci` badge showed failing on every run in its history -
all 12, from the very first real code commit through the latest. The
cause turned out to be exactly the kind of gap that's easy to miss
because a development sandbox and CI runner silently diverge:
`.github/workflows/ci.yml` goes straight from `actions/checkout` to
`pip install`, with no step installing any system-level (apt) package
at all. `packages/core/redactguard_core/detectors/text`'s OCR detector
calls `pytesseract`, which shells out to a real `tesseract` binary -
that's a system package, not something `pip install`able on its own.
GitHub's `ubuntu-latest` runner doesn't ship `tesseract-ocr`
preinstalled, so every test touching the OCR detector failed with
`pytesseract.pytesseract.TesseractNotFoundError` on every single CI
run, on all three Python versions in the matrix, since the commit that
first wired OCR in.

This exact system-dependency gap had already been found and fixed once
before - `docker/Dockerfile` and `docker/Dockerfile.webapp` both
`apt-get install ffmpeg tesseract-ocr` (see ADR-0010, "missing
tesseract-ocr fix") - but that fix was never carried over to the CI
workflow that runs the test suite directly on the runner rather than
inside either Docker image. Every "full verification" pass this project
ran throughout development - lint, mypy, pytest, even a from-scratch
venv install mirroring CI's `pip install` steps exactly - passed locally
every time, because the local sandbox already had `tesseract-ocr`
installed at the OS level from the start. Nothing in that local
verification loop ever exercised a machine without it, so this drifted
silently for the project's entire history without once surfacing
locally.

## Decision

Added an `apt-get install ffmpeg tesseract-ocr` step to `ci.yml`,
between `actions/setup-python` and the `pip install` step - the same
two packages the Docker images already install, for the same reason.
`ffmpeg` is technically already present on `ubuntu-latest` runners
today, but it's listed explicitly anyway so this step doesn't rely on
that continuing to be true.

Verified the actual failure mode directly rather than only reasoning
about it: temporarily moved `/usr/bin/tesseract` out of the way in this
development sandbox and re-ran `packages/core/tests/test_ocr_detector.py`,
which reproduced `TesseractNotFoundError` exactly - then restored the
binary and confirmed the same tests pass again. This is the same
failure GitHub's runner would hit without this fix, reproduced on
purpose rather than inferred from reading the workflow file alone.

## Consequences

CI should now go green on the next push - a claim being made carefully
here rather than confidently, because this project's own recent history
is a reminder that "verified locally" and "verified in the actual CI
environment" aren't the same claim; the honest way to close this out is
to watch the next real run, not to declare it fixed from a diff.

Worth calling out explicitly for anyone reading this project's history:
the badges on the README were reporting the true state the entire time.
An earlier attempt to diagnose this by having a tool fetch and
summarize the GitHub Actions pages reported every run as green - wrong,
contradicted moments later by a plain screenshot of the same page
showing red across the board. The tool's HTML-to-text conversion most
likely dropped the actual status icon/label before summarization ever
saw it, leaving a summarizing model to guess from commit-message tone
rather than real content - a fabricated-sounding "success" that read as
confident and was simply false. The lesson carried forward: a status
icon, badge color, or other purely-visual signal needs a screenshot or
a real API/log fetch, not an HTML-to-markdown summary, and a
surprising "everything's fine" result asking to be re-verified rather
than reported.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
