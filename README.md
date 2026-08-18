<!-- RedactGuard | Author: Ritesh Ambastha -->

# RedactGuard

**A self-hosted, privacy-preserving video PII redaction toolkit.**

RedactGuard detects and redacts personally identifiable information in
video — faces, on-screen text/documents (including license plates), and
spoken PII in audio — entirely on infrastructure you control. No frame or
transcript ever leaves the machine it runs on.

## Why RedactGuard is different

- **Ensemble detection.** Every PII type is checked by 2-3 independent
  detectors that vote on agreement, rather than trusting a single model's
  blind spots.
- **Closed-loop verification.** After redaction, RedactGuard re-scans its
  own output with the same detection+voting pass. If anything is still
  flagged, a retry controller escalates settings and re-redacts — up to
  N attempts — before finalizing. See
  [`docs/adr/0002-mandatory-verify-then-retry-loop.md`](docs/adr/0002-mandatory-verify-then-retry-loop.md).
- **Policy-as-code.** Compliance profiles (GDPR, CCPA, or your own) are
  versioned YAML, not hidden thresholds. See [`policies/`](policies/).
- **Plugin architecture.** New PII detectors register via a small SDK
  (`redactguard-plugin-sdk`) — no core changes required.
- **Human-in-the-loop by design.** If verification can't fully resolve a
  file, RedactGuard still emits it, with a loud "unresolved" warning in
  the audit report — it never silently hides a failure, and never
  silently withholds your data either.

## Status

Early scaffold. The pipeline architecture, data models, policy schema,
and plugin registry are in place; detector implementations (face/text/audio)
land in the next phase. See [`docs/architecture.md`](docs/architecture.md)
and the ADR log in [`docs/adr/`](docs/adr/) for the reasoning behind each
design decision.

## Repository layout

This is a monorepo with three installable packages:

- [`packages/core`](packages/core) (`redactguard-core`) — the detection,
  ensemble voting, redaction, and verification pipeline.
- [`packages/cli`](packages/cli) (`redactguard-cli`) — a thin CLI
  (`redactguard scan|run`) over `core`.
- [`packages/plugin-sdk`](packages/plugin-sdk) (`redactguard-plugin-sdk`) —
  base classes and a registration API for third-party detectors.

## License

Apache 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

## Maintainer

Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))


---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
