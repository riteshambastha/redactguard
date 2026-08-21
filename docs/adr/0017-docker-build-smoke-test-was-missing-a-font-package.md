<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0017. docker-build has failed on every run since the hardening commit - a missing font package, not the non-root user switch

- Status: Accepted
- Author: Ritesh Ambastha

## Context

The `docker-build` workflow's real run history (confirmed from an actual
screenshot of the GitHub Actions run list, not an automated summary of
the page - see the note at the end of ADR-0016 about why that distinction
matters here) shows runs #2-#4 green, then every run from #5 onward red,
starting exactly at the "Harden Docker images: non-root user, missing
tesseract-ocr/policies fix, real GPU device wiring" commit and persisting
through every commit since.

That commit's own message is explicit that it was never build- or
run-verified: this development sandbox cannot reach any container
registry (403 on Docker Hub, ghcr.io, and mirror.gcr.io alike), so
`docker build`/`docker run` were never actually exercised here before
that commit shipped - only reasoned about from reading the Dockerfiles.
The same registry block is still true today, confirmed again while
investigating this: `docker build -f docker/Dockerfile .` fails
immediately trying to pull `python:3.11-slim`
(`403 Forbidden` from `registry-1.docker.io`), before a single instruction
in the Dockerfile even runs.

The commit's most visible change was switching both images to a
non-root `USER redactguard`, which was the natural first suspect. It
isn't the cause: the smoke test's own writes all target `/tmp`, which is
world-writable, and nothing else the pipeline touches at scan time
depends on root. The real break is in `docker/smoke_test.sh`, added by
the very same commit and never actually run anywhere before now:

```
ffmpeg -y -f lavfi -i "color=c=white:s=320x240:d=2" \
    -vf "drawtext=text='SSN 123-45-6789 on file':...` \
    -r 4 /tmp/smoke_clip.mp4
```

`drawtext` with no `fontfile=` resolves a font by *family name*
("Sans") through fontconfig at runtime - which requires an actual font
file to be registered somewhere fontconfig looks. Both Dockerfiles build
with `apt-get install -y --no-install-recommends ffmpeg tesseract-ocr`
only; neither installs any font package, and `--no-install-recommends`
specifically means nothing pulls one in as a side effect either. This
sandbox's own shell has fonts installed already (for unrelated reasons),
so `_make_text_video`-style fixtures using this exact same `drawtext`
pattern in `test_cli_smoke.py`, `test_orchestrator_run.py`, and
`webapp/tests/conftest.py` all passed locally - the same "verified
locally, but the local environment happens to have something the target
environment doesn't" gap ADR-0016 already hit once with `tesseract-ocr`,
just with a font instead of a binary this time, and in the Docker image
rather than the CI runner.

Reproduced the actual failure directly rather than only reasoning about
it, working around this sandbox's registry block by simulating the
Docker image's font-less environment locally instead of inside a real
container: pointed `FONTCONFIG_FILE` at a config with zero `<dir>`
entries (so fontconfig can resolve *nothing*, matching a container with
no font package installed) and re-ran the exact `drawtext` command from
`smoke_test.sh`. It failed exactly as hypothesized:

```
[Parsed_drawtext_0] Cannot find a valid font for the family Sans
[AVFilterGraph] Error initializing filters
Error opening output file /tmp/test_smoke_clip_nofont.mp4.
```

Re-ran the same command with an explicit `fontfile=` pointing at a real
font path, still under the same zero-font fontconfig environment - it
succeeded, proving `fontfile=` bypasses the broken lookup entirely. Then
ran the *entire* `docker/smoke_test.sh` script end-to-end (ffmpeg
generation, the real `redactguard scan` CLI command against
`policies/gdpr_v1.yaml`, and the span-count assertion) under the same
font-less `FONTCONFIG_FILE` override, with the fix applied - it passed,
detecting 3 spans, exactly mirroring what the CI job runs inside the
container.

## Decision

Added `fonts-dejavu-core` to both Dockerfiles' apt-get install list
(next to `ffmpeg`/`tesseract-ocr`, for the same "the image needs this,
don't rely on it happening to be there" reason as ADR-0016), and pinned
`docker/smoke_test.sh`'s `drawtext` call to an explicit
`fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf` instead of
letting fontconfig guess. Applied the same `fontfile=` pin to the three
test fixtures using this identical pattern
(`test_cli_smoke.py::_make_text_video`,
`test_orchestrator_run.py::_make_text_video`,
`webapp/tests/conftest.py::text_pii_clip`) and added `fonts-dejavu-core`
to `ci.yml`'s system-dependency install step so the path those fixtures
now hardcode is guaranteed to exist there too, rather than trusting
whatever GitHub's `ubuntu-latest` image happens to ship. `docker/
Dockerfile.gpu` gets the same package for parity, even though its CI job
is build-only today (no GPU on GitHub-hosted runners to run-smoke-test
against) - nothing should stop someone running `smoke_test.sh` against
it by hand later.

The redaction pipeline itself never calls `drawtext` - only the smoke
test and its test-fixture equivalents do, to synthesize fake PII for
detection to find - so this fix touches test/CI infrastructure only, not
product code.

## Consequences

`docker-build` should go green on the next push for `build-cpu`; this is
stated carefully, the same way ADR-0016 stated the `ci` fix carefully -
this sandbox still cannot pull a base image or run a real container
(the registry 403 is unchanged), so the closest verification available
here is the font-less-environment reproduction described above, which
exercises the *exact* failing command and the *exact* fix, plus the real
`redactguard scan` CLI end-to-end, but is still not a literal `docker
build && docker run` of the shipped image. Watching the next real
`docker-build` run remains the honest way to close this out, not this
ADR's claim alone.

Worth naming directly: this is the second time in two ADRs that "passed
every local check" and "will actually work in CI" turned out to be
different claims, for the same underlying reason both times - a system-
level resource (a binary, a font file) that this development sandbox
happens to already have, silently propping up code that never installs
it. Anywhere else in this project that shells out to `ffmpeg`/`tesseract`
with an implicit environment assumption is worth the same scrutiny
before trusting it in a fresh environment.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
