<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0003. Policy-as-code: versioned compliance profiles

- Status: Accepted
- Author: Ritesh Ambastha

## Context

Redaction rules (which PII types, thresholds, retry limits, custom keywords) differ by use case and by regulatory regime (GDPR vs. CCPA vs. an internal policy).

## Decision

Express rules as versioned, named YAML profiles under `policies/` (e.g. `gdpr_v1.yaml`), loaded and validated via `pipeline/policy.py`, rather than one generic config file.

## Consequences

Slightly more ceremony than a single config, in exchange for auditability (a run references an exact, versioned policy) and easy multi-tenant/multi-client use.


---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
