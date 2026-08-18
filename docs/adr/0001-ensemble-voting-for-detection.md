<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0001. Ensemble voting for PII detection

- Status: Accepted
- Author: Ritesh Ambastha

## Context

A single detector per PII type means the whole system inherits that one model's blind spots (angle, lighting, occlusion, language coverage).

## Decision

Run 2-3 independent detectors per PII type and aggregate via an agreement-threshold voting module (`ensemble/voting.py`) rather than trusting any single model.

## Consequences

More compute per file and more integration surface, in exchange for materially better recall and a defensible "we cross-check" story for the audit report.


---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
