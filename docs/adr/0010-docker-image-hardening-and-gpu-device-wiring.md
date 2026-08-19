<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0010. Docker image hardening and GPU device wiring

- Status: Accepted
- Author: Ritesh Ambastha

## Context

`docker/Dockerfile` (CPU) and `docker/Dockerfile.gpu` existed but had never
been build- or run-verified against a real container registry. Attempting
to actually do that verification in this project's development sandbox
failed outright: `docker build` on either file returns 403 Forbidden
pulling the base image, from `registry-1.docker.io`, `ghcr.io`, and
`mirror.gcr.io` alike - this sandbox has no container-registry network
access at all, full stop, not a flaky-mirror problem. That's a real,
disclosed limitation of *this* development environment, not something
worked around or hidden; it means everything below was found and fixed by
static code review, not by observing an actual failing build.

That review surfaced several real, independent problems:

1. **`docker/Dockerfile.gpu` was missing `tesseract-ocr`** from its apt
   install list. `docker/Dockerfile` (CPU) had it; the GPU variant had
   silently drifted and would fail on any `document`/`text` policy the
   moment `pytesseract` tried to shell out to a binary that isn't there.
2. **Neither Dockerfile copied `policies/` into the image.** Only
   `packages/` was copied. `redactguard scan --policy policies/gdpr_v1.yaml`
   - the exact command in this project's own README quickstart - would
   404 inside either container on its own shipped default policy. A
   user's own custom policy mounted via `-v` would still work, which is
   likely why this went unnoticed, but the advertised out-of-the-box path
   was broken.
3. **Both images ran as root.** Nothing in the entrypoint needs root, and
   this tool exists specifically to process sensitive video content -
   running as root is an avoidable privilege-escalation surface for no
   benefit.
4. **`WhisperAudioDetector` hardcoded `device="cpu"` in `_get_model()`.**
   This is the most consequential finding: it meant `Dockerfile.gpu` -
   the entire point of which is GPU acceleration - provided *zero* actual
   speedup under any configuration whatsoever. The "optional GPU image"
   was, functionally, a CPU image with a larger base layer and an unused
   `--gpus all` flag.

## Decision

Fix all four directly, plus add real CI coverage so future drift is
caught automatically instead of by the next person auditing the Dockerfile
by hand:

- Added `tesseract-ocr` to `docker/Dockerfile.gpu`'s apt install list, so
  it matches the CPU image's.
- Added `COPY policies/ policies/` to both Dockerfiles.
- Added a non-root `redactguard` user (`useradd --create-home --shell
  /usr/sbin/nologin redactguard` + `USER redactguard`) to both.
- Changed `WhisperAudioDetector.__init__` to read `device`/`compute_type`
  from `REDACTGUARD_WHISPER_DEVICE` / `REDACTGUARD_WHISPER_COMPUTE_TYPE`
  environment variables, defaulting to the original `"cpu"`/`"int8"` when
  unset (so existing behavior is unchanged unless a caller opts in) and to
  `"float16"` for compute type when `device` is `"cuda"` and no explicit
  compute type is given. `docker/Dockerfile.gpu` now documents setting
  `REDACTGUARD_WHISPER_DEVICE=cuda` at `docker run` time as the actual way
  to get GPU acceleration. Two new tests
  (`test_defaults_to_cpu_int8_when_no_env_vars_set`,
  `test_device_and_compute_type_are_configurable_via_env_vars`) cover the
  wiring itself, without needing real CUDA hardware.
- Added `.github/workflows/docker-build.yml`: a `build-cpu` job that
  builds the CPU image and then actually runs it twice - a `--help`
  sanity check, and a real scan against a synthetic ffmpeg-generated clip
  (`docker/smoke_test.sh`) that asserts at least one PII span comes back -
  and a `build-gpu` job that builds (but does not run) the GPU image,
  since standard GitHub-hosted runners have no GPU hardware to run it on.
  `smoke_test.sh` is bind-mounted read-only as a single file rather than
  copied into the shipped image, and writes exclusively to `/tmp` inside
  the container, specifically to avoid a host/container UID permission
  mismatch against the new non-root `USER redactguard` - a host-mounted
  output directory would otherwise risk the container's non-root UID being
  unable to write to it.

## Consequences

The CPU image now gets a real, automatic run-verification on every push
that touches `docker/**` or `packages/**` - something that was previously
untested end-to-end. This is expected to be the first time either
Dockerfile is actually built and run against a real registry, since that
capability doesn't exist in this development sandbox at all.

The GPU image remains build-only in CI, and carries an explicit,
undismissed caveat: `ctranslate2` (faster-whisper's backend) needs cuDNN
shared libraries at runtime, and the `nvidia/cuda:12.4.1-runtime-ubuntu22.04`
base tag this Dockerfile uses ships the CUDA runtime but *not* cuDNN. This
has not been verified - not build, not run - anywhere, because the
sandbox that built it has no registry access and GitHub's own runners
have no GPU. Before relying on this image for real GPU inference, whoever
runs it first should confirm the cuDNN version ctranslate2 was built
against and either switch to a matching `*-cudnn*-runtime-*` NVIDIA base
image tag or install the matching `libcudnn` packages via apt. This ADR
records that gap explicitly rather than presenting the GPU image as more
verified than it is.

Everything in this ADR - the four bug fixes, the new CI jobs, and the
Whisper device wiring - was found and written through static code review
and unit tests, not through an actual `docker build`/`docker run` in this
session. The real verification happens the next time CI runs on GitHub
Actions, which (unlike this sandbox) has full container-registry access.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
