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

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY packages/ packages/
RUN pip install --no-cache-dir -e packages/core -e packages/cli -e packages/plugin-sdk

ENTRYPOINT ["redactguard"]
CMD ["--help"]

# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
