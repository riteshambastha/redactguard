<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0004. Plugin registry for detectors

- Status: Accepted
- Author: Ritesh Ambastha

## Context

New PII categories (tattoos, badges, ID cards, ...) will come up over time; the core pipeline shouldn't need to change to support them.

## Decision

Detectors implement `AbstractDetector` (from `redactguard-plugin-sdk`) and register via `@register_detector("<pii_type>")`, or via a `redactguard.detectors` entry point for out-of-tree, pip-installable plugins (`detectors/registry.py`).

## Consequences

A small amount of indirection in exchange for real extensibility - third parties can ship a detector as its own package.


---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
