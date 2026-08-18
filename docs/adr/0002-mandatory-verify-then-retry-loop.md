<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0002. Mandatory verify-then-retry loop, human-in-the-loop on exhaustion

- Status: Accepted
- Author: Ritesh Ambastha

## Context

Redaction can itself be imperfect - a blurred region can be too small, or a new detection pass can catch what the first pass missed. A tool that claims to redact PII needs a way to check its own work.

## Decision

After redaction, re-run detection+voting on the output (`verification/verifier.py`). If anything is still flagged, escalate settings and re-redact just those regions (`verification/retry_controller.py`), up to `retry.max_attempts`. If still unresolved, emit the output anyway with a prominent "unresolved" warning in the audit report for human review - never hard-fail and withhold the file.

## Consequences

Meaningfully stronger guarantee than "redact once and hope", at the cost of a second full detection pass (and possibly more) per file. The human-in-the-loop choice on exhaustion trades a false sense of automated safety for an honest, reviewable signal.


---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
