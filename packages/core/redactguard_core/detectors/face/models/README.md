<!-- RedactGuard | Author: Ritesh Ambastha -->

# Vendored model: `haarcascade_frontalface_default.xml`

Sourced from the OpenCV project
(https://github.com/opencv/opencv/blob/4.x/data/haarcascades/haarcascade_frontalface_default.xml),
under OpenCV's own license (embedded in the file header - an Intel/BSD-style
license permitting redistribution). Vendored directly in this repo rather
than relying on the `opencv-python` package to bundle it, because it
doesn't in some builds - see `docs/adr/0006-vendor-haar-cascade.md`.

This keeps `redactguard-core`'s face detector fully self-hosted with zero
runtime network dependency, consistent with the rest of RedactGuard's
"nothing leaves premises" design.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
