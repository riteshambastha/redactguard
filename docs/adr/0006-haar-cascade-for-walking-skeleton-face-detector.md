<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0006. Haar cascade (not a DNN model) for the walking-skeleton face detector, vendored in-repo

- Status: Accepted
- Author: Ritesh Ambastha

## Context

ADR-0005 flagged Ultralytics YOLOv8 (AGPL-3.0) as a face-detector option to
avoid, and pointed at RetinaFace as a permissively-licensed alternative.
RetinaFace, mediapipe's Tasks API, and most modern DNN face detectors all
need a model file downloaded at setup or first run - fine in production or
CI, but the sandbox this walking-skeleton phase was built and tested in
could only reach PyPI and `raw.githubusercontent.com`, not the CDNs those
downloads use (`storage.googleapis.com`, Hugging Face Hub, etc.) - so a
DNN-based detector couldn't be verified end-to-end here.

## Decision

Use OpenCV's Haar-cascade frontal-face detector for the first (single,
walking-skeleton) face detector. The cascade XML is a ~900KB file
vendored directly in `detectors/face/models/` (sourced from the OpenCV
project, BSD/Intel-licensed, redistribution permitted - see that
directory's README), rather than relying on `opencv-python` to bundle it
(it doesn't, in the build used here) or downloading a model at runtime.
This keeps the detector fully offline with zero setup step, consistent
with RedactGuard's "nothing leaves premises" design, and let it actually
be tested against real generated video in this environment.

## Consequences

Haar cascades are meaningfully less accurate than a modern DNN detector -
more false negatives on non-frontal faces, poor lighting, or small faces.
This is an accepted, documented tradeoff for the first ensemble slot
(docs/threat_model.md), not a permanent choice: adding a DNN-based
detector (RetinaFace or mediapipe, per ADR-0005's original direction) as
the *second* detector is the natural next step once running somewhere
with normal internet access (Docker build, CI, or production), at which
point it also starts satisfying ADR-0001's ensemble-voting requirement
for this PII type.

One more reason the vendored-file approach turned out to be the right
call: `opencv-python>=5.0` removed `cv2.CascadeClassifier` entirely (in
favor of the ONNX-based `cv2.FaceDetectorYN`, which itself needs a
downloaded model - the same problem all over again). `redactguard-core`
pins `opencv-python-headless<5` for this reason; revisit this pin
alongside adding the DNN second detector.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
