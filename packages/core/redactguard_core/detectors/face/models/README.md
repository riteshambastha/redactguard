<!-- RedactGuard | Author: Ritesh Ambastha -->

# Vendored models

## `haarcascade_frontalface_default.xml`

Sourced from the OpenCV project
(https://github.com/opencv/opencv/blob/4.x/data/haarcascades/haarcascade_frontalface_default.xml),
under OpenCV's own license (embedded in the file header - an Intel/BSD-style
license permitting redistribution). Vendored directly in this repo rather
than relying on the `opencv-python` package to bundle it, because it
doesn't in some builds - see `docs/adr/0006-vendor-haar-cascade.md`.

Used by `HaarFaceDetector` (`detector_name="opencv-haar-cascade"`).

## `lbpcascade_frontalface_improved.xml`

Also sourced from the OpenCV project
(https://github.com/opencv/opencv/blob/4.x/data/lbpcascades/lbpcascade_frontalface_improved.xml),
copyright Puttemans Steven, Can Ergun and Toon Goedeme (KU Leuven, EAVISE
Research Group), under the BSD-style Contributors License Agreement
embedded in the file header - redistribution permitted with attribution.

Used by `LbpFaceDetector` (`detector_name="opencv-lbp-cascade"`) as the
*second*, algorithmically-independent face detector - Local Binary
Patterns rather than Haar wavelets - so ensemble voting (ADR-0001,
ADR-0008) has a genuine second opinion instead of running the same
detection logic twice. Its different feature representation also gives
it different failure modes (lighting/rotation sensitivity differs from
Haar's), which is the actual point of pairing them.

Both files keep `redactguard-core`'s face detectors fully self-hosted with
zero runtime network dependency, consistent with the rest of RedactGuard's
"nothing leaves premises" design.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
