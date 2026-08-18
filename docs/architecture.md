<!-- RedactGuard | Author: Ritesh Ambastha -->

# RedactGuard architecture

## Pipeline flow

```
input (file or folder)
    -> ingest        (ffmpeg/PyAV demux, frame sampling, batch/folder walk)
    -> detect         (ensemble: 2-3 detectors per PII type: face / text / audio)
    -> vote           (agreement-threshold consensus -> trusted PII spans)
    -> [scan stops here: JSON manifest, no video modified]
    -> redact         (blur/pixelate video regions, mute/beep audio spans)
    -> verify         (re-run detect+vote on the redacted draft)
    -> retry?          (verifier flagged something -> escalate settings,
                         re-redact just those regions, up to N attempts)
    -> report         (manifest + verification results + retry count;
                        "unresolved" warning if N attempts exhausted)
```

## Packages

- `redactguard-core` — `pipeline/`, `detectors/`, `ensemble/`, `redaction/`,
  `verification/`. See the module layout in the README.
- `redactguard-cli` — thin wrapper exposing `redactguard scan|run`.
- `redactguard-plugin-sdk` — `AbstractDetector` + the registration API for
  third-party detector plugins.

## Design decisions

Each non-obvious choice here has a corresponding ADR in `docs/adr/` —
start there before assuming a decision was accidental.


---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
