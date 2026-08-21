# RedactGuard - CPU image
#
# Part of RedactGuard - a self-hosted, privacy-preserving video PII
# redaction toolkit with ensemble detection and a closed-loop
# verify-then-retry guardrail.
#
# Author: Ritesh Ambastha

FROM python:3.11-slim

# Model weights are downloaded from the model hub and cached in a volume
# on first run - not baked into this image (see docs/adr/, build-plan log).

# fonts-dejavu-core: not needed by the redaction pipeline itself, but the
# CI smoke test (docker/smoke_test.sh) uses ffmpeg's drawtext filter to
# synthesize a fake PII clip, which needs a real font file on disk
# regardless of --no-install-recommends. See docs/adr/0017.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        tesseract-ocr \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY packages/ packages/
# Shipped compliance profiles (policies/gdpr_v1.yaml etc.) - without this,
# `redactguard scan --policy policies/gdpr_v1.yaml` inside the container
# would 404 on its own default policy files (found by code review while
# auditing this Dockerfile - see docs/adr/0010; a user's own custom policy
# mounted via -v would still work fine either way).
COPY policies/ policies/
RUN pip install --no-cache-dir -e packages/core -e packages/cli -e packages/plugin-sdk

# Run as a non-root user - nothing here needs root, and this tool exists
# to handle sensitive video content.
RUN useradd --create-home --shell /usr/sbin/nologin redactguard
USER redactguard

ENTRYPOINT ["redactguard"]
CMD ["--help"]

# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
