<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0007. Composite redaction at the source's native frame rate, not `sample_fps`

- Status: Accepted
- Author: Ritesh Ambastha

## Context

Detection samples frames at a policy-configurable `sample_fps` (the dev
policy uses 1.0) - running every detector at the source's full native
frame rate would be needlessly expensive, especially for the Whisper
audio path and any future DNN-based visual detector.

`Orchestrator.run()` needs to produce an actual redacted video, though,
and naively re-encoding only the sampled frames would downgrade a
30fps source to a 1fps output - a real, visible quality loss purely as
an artifact of how detection was optimized, not anything intrinsic to
redaction itself.

## Decision

`Orchestrator.run()` decodes the source twice, for two different
purposes: once at `sample_fps` for detection (cheap, run once, reused
across every retry's re-vote), and once at the source's own native frame
rate (`ingest.get_frame_rate()` + `sample_frames()`) purely for redaction
compositing. Each detected `PiiSpan`'s single timestamp is treated as
covering a `[start - half_window_s, end + half_window_s]` window, where
`half_window_s = 0.5 / sample_fps` - half a detection period on either
side, so consecutive detection samples tile the timeline without gaps or
overlaps. Every native-fps frame whose timestamp falls in that window for
a given span gets redacted with that span's bbox (widened by the retry
controller's margin - see ADR-0002). The redacted native frames are then
re-encoded via ffmpeg (`redaction/muxer.py::encode_video_from_frames`) and
remuxed with the (separately redacted) audio track.

## Consequences

Output video keeps the source's native frame rate and smoothness - no
detection-driven quality loss. The cost is decoding the source twice
(sample_fps once, native fps once) and doing a full ffmpeg image-sequence
re-encode per retry attempt, which is real but acceptable for a
walking-skeleton/demo-scale tool; a production deployment processing long
footage would want to decode natively once and reuse the frame buffer
across retries rather than re-decoding, and would likely want a
persistent-worker frame cache. That optimization is out of scope here.

The half-window temporal-coverage heuristic is a deliberate approximation
tied to how sparse `sample_fps` is - it assumes a detected face/text
region persists (spatially, in the same bbox) for the full window, which
is reasonable at 1fps for typical footage but degrades if the subject
moves quickly between samples. A future ensemble slot doing multi-frame
tracking (rather than frame-independent detection) would let this become
exact instead of approximate.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
