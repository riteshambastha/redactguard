#!/bin/sh
# RedactGuard - CI smoke test, run *inside* the built image
#
# Part of RedactGuard - a self-hosted, privacy-preserving video PII
# redaction toolkit with ensemble detection and a closed-loop
# verify-then-retry guardrail.
#
# Not copied into the shipped image - .github/workflows/docker-build.yml
# bind-mounts this single file read-only and executes it, so a broken
# image (missing apt package, bad ENTRYPOINT, a policy file that never
# got COPYed in - see docs/adr/0010) fails CI instead of shipping.
#
# Author: Ritesh Ambastha

set -e

# fontfile= is required, not cosmetic: ffmpeg's drawtext filter otherwise
# resolves fonts by *family name* through fontconfig, which needs an
# actual font file registered somewhere fontconfig looks - and this image
# is built with --no-install-recommends, so nothing pulls one in "for
# free" the way a full desktop/dev environment would. Reproduced for real
# (not just reasoned about) by pointing FONTCONFIG_FILE at a config with
# zero <dir> entries and rerunning this exact command: ffmpeg fails with
# "Cannot find a valid font for the family Sans" and exits non-zero -
# exactly what broke this smoke test (and this job) on every docker-build
# run since the non-root/hardening commit added it. See docs/adr/0017.
ffmpeg -y -f lavfi -i "color=c=white:s=320x240:d=2" \
    -vf "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='SSN 123-45-6789 on file':fontcolor=black:fontsize=20:x=10:y=100" \
    -r 4 /tmp/smoke_clip.mp4

redactguard scan /tmp/smoke_clip.mp4 --policy policies/gdpr_v1.yaml --out /tmp/smoke_manifest.json

python3 -c "
import json
m = json.load(open('/tmp/smoke_manifest.json'))
assert m['spans'], f'expected at least one detected span, got: {m}'
print('OK -', len(m['spans']), 'span(s) detected inside the container')
"

# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
