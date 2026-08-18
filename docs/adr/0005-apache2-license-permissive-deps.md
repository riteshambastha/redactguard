<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0005. Apache-2.0 license; avoid copyleft dependencies

- Status: Accepted
- Author: Ritesh Ambastha

## Context

A natural face-detector choice (Ultralytics YOLOv8) is AGPL-3.0. Depending on it would put pressure on the whole project's licensing story.

## Decision

License RedactGuard itself under Apache-2.0, and prefer permissively-licensed detector backends (e.g. RetinaFace) over AGPL-3.0 dependencies, to keep the full dependency tree permissive.

## Consequences

Slightly more work to find/validate permissive alternatives, in exchange for a repo that's unambiguously easy for anyone - including companies - to adopt or contribute to.


---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
