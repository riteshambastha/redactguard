<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0008. A second, algorithmically-independent detector per PII type, and the spatial-agreement fix that made it meaningful

- Status: Accepted
- Author: Ritesh Ambastha

## Context

Every PII type shipped with exactly one detector through the walking-skeleton
phase (ADR-0006, ADR-0007), so `policies/walking_skeleton_dev.yaml` ran with
`agreement_threshold=1` - the real profiles (`gdpr_v1.yaml`, `ccpa_v1.yaml`,
`custom_template.yaml`) already specified the intended default of 2, but
nothing could actually reach it: ADR-0001's whole premise, that independent
detectors corroborating each other reduces false positives, was unenforced.

Auditing `ensemble/voting.py` while adding a second detector surfaced a real
bug: `_overlaps()` only checked *time*, never space. Two different faces
detected in the same one-second sample would have incorrectly "agreed"
purely because both fired in that sample - agreement_threshold=2 would have
been satisfiable by two detectors looking at *unrelated* regions of the same
frame, which defeats the entire point.

## Decision

Add a second, algorithmically-independent detector per PII type, each
specifically chosen to fail differently from the first rather than just
existing for a headcount:

- **face**: `LbpFaceDetector` (Local Binary Patterns) alongside the existing
  `HaarFaceDetector` (Haar wavelets) - different feature representations,
  different lighting/rotation sensitivity.
- **text**: `MserTextRegionDetector` (OpenCV MSER blob detection - purely
  structural, no OCR at all) alongside `TesseractOcrDetector` (semantic).
  Tesseract can hallucinate readable words out of noise; requiring a
  structurally-independent detector to also see *something* at that location
  catches that failure mode.
- **audio**: `EnergyVadDetector` (short-time RMS energy thresholding - no
  transcription) alongside `WhisperAudioDetector` (semantic ASR). Whisper can
  hallucinate plausible words from silence or background music; requiring
  real energy at that timestamp catches that failure mode. Unlike Whisper,
  this needs no model download, so unlike the ASR path it's fully verified
  end-to-end in this sandbox.

`ensemble/voting.py` was fixed alongside this: `_overlaps()` now also
requires IoU (intersection-over-union) above `DEFAULT_IOU_THRESHOLD=0.1` for
any pair of detections that both carry a bbox; bbox-less types (audio) keep
the temporal-only check. The threshold is deliberately loose - two
algorithmically-different detectors rarely draw near-identical boxes around
the same real region, and a strict IoU would defeat the point of pairing
diverse detectors. A voted span's bbox is now the *union* of every
contributing detection's box (`_union_bbox`), not an arbitrary single
contributor's box, so the redaction actually covers what either detector saw.

## Consequences

Real ensemble voting at `agreement_threshold=2` is now possible and is what
the shipped policies use. `policies/walking_skeleton_dev.yaml` keeps
`agreement_threshold=1` purely as a documented dev/debug convenience for
iterating on a single detector.

Running two real detectors per PII type end-to-end for the first time (a
single-detector ensemble had never exercised this) surfaced a more
fundamental bug than the spatial one above: `_overlaps()`'s temporal check
used a strict `<` (`a.start_time_s < b.end_time_s and b.start_time_s <
a.end_time_s`). Every built-in detector reports a single instant per frame
(`start_time_s == end_time_s`), and two zero-length intervals at the exact
same instant never satisfy a strict `<` against each other - `0.0 < 0.0` is
`False`. That meant two detectors examining the *same frame* could never be
considered to agree, no matter how perfectly their boxes lined up spatially;
`agreement_threshold=2` was silently unsatisfiable for every point-in-time
detection, which is all of them. Fixed by using `<=` for the temporal check
(a minor, acceptable side effect: two genuinely back-to-back non-overlapping
intervals like `[0, 1)` and `[1, 2)` now count as touching at the boundary
instant). This is the fix that actually makes `agreement_threshold=2` work
in practice - it was found by scanning a real ffmpeg-rendered clip with
`redactguard scan` and getting zero spans back for text that was plainly
there, then tracing the two detectors' raw output down to a single
comparison operator.

A genuinely interesting finding from running this end-to-end (see
`test_orchestrator_run.py`): on a real rendered-text clip, Tesseract's
word-level OCR bbox and MSER's finer sub-word/character regions often don't
share enough spatial overlap to satisfy `agreement_threshold=2` on the
*first* pass - different detectors segmenting "what counts as one region"
differently is a real, expected consequence of picking algorithmically
diverse detectors, not a bug to special-case away. This turned out to
matter in practice, not just in theory: it's exactly what the closed-loop
retry/escalation system (ADR-0002) exists to absorb - `RetryController`
progressively lowers the agreement threshold and widens the margin until
either something redacts cleanly or `max_attempts` is exhausted (never
withholding output either way). Finding this interaction is also what
surfaced a real off-by-one in `RetryController.escalate()`: the first
escalation call (`attempt=0`, meaning verification had already failed once)
was computing `base_agreement_threshold - attempt` = `base - 0`, i.e. no
actual reduction on the very first retry - it now computes
`base - (attempt + 1)`, so the first retry genuinely escalates instead of
repeating the same settings for a wasted attempt.

`MserTextRegionDetector` also needed two cleanup passes that weren't in the
original design. First, a real non-max-suppression pass (`_non_max_suppress`):
raw MSER output returns many nested/near-duplicate regions per real blob (a
word, several of its characters, and their sub-strokes are all independently
"stable" regions to the algorithm). Without collapsing those first, a single
frame could produce dozens of near-identical detections - harmless at
`agreement_threshold=2` (they still only count as one distinct detector
name) but pointless noise, and actively counterproductive at the dev
policy's `agreement_threshold=1`, where every nested region became its own
throwaway redaction target. Second, a horizontal line-merge pass
(`_merge_horizontally_adjacent`): even after NMS, MSER's surviving boxes are
still per-character/word, while Tesseract's OCR bbox is word/phrase-level -
too fine a granularity mismatch to reliably clear the IoU threshold above,
independent of the temporal bug. Merging boxes that share a line and sit
close together horizontally into one line-level box (with a bounded number
of passes, since a single sweep can miss transitive merges - box A joining B
can bring the combined box within reach of C) brought MSER's output to
roughly the same granularity as Tesseract's, so the two agree on real text
instead of needing the retry loop to save them every time.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
