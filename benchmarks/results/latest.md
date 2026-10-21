<!-- RedactGuard | Author: Ritesh Ambastha -->

# Latest benchmark results

## On-screen text PII (synthetic), October 2026

Script: [`benchmarks/text_pii_benchmark.py`](../text_pii_benchmark.py)

**Setup.** Synthetic 1280×720 frames with emails, phone numbers, SSNs and
credit-card numbers drawn at known positions, mixed with ordinary non-PII
text ("Weekly specials", "Meeting notes", ...). Backgrounds are plain,
gradient or cluttered (blurred blocks plus noise); font sizes 22–48 px;
about 20% of frames use low-contrast text. Every fifth frame contains no
PII at all, only ordinary text, to measure false alarms. Two random seeds
(7 and 11), 150 frames each: **300 frames, 491 PII instances.**

A PII instance counts as found when a detection box overlaps its
ground-truth box.

### Frame-level detection (first pass)

| Detector / vote | PII found | Seed 7 | Seed 11 |
|---|---|---|---|
| Tesseract OCR alone | 317 / 491 (65%) | 72% | 58% |
| MSER text-region detector alone | 341 / 491 (69%) | 70% | 69% |
| Either detector (`agreement_threshold=1`) | 443 / 491 (90%) | 94% | 87% |
| Both detectors (`agreement_threshold=2`, default) | 156 / 491 (32%) | 34% | 29% |

### False alarms

| Vote | Non-PII spans flagged | PII-free frames flagged |
|---|---|---|
| Either detector | 917 | 52 / 60 (87%) |
| Both detectors | 0 | 0 / 60 (0%) |

### End-to-end (`Orchestrator.run`, seed 7, 40 scenes)

| Measure | Result |
|---|---|
| PII strings readable by OCR in the source | 36 of 62 |
| PII strings readable by OCR after redaction | 1 of 62 |
| Verifier spans flagged per attempt | 195 → 86 → 57 → 45 |
| Final status | `unresolved = true` |

### Reading the results

- The default strict vote produces no false alarms but finds only about a
  third of on-screen PII on the first pass. The verify-then-retry loop
  (ADR-0002) is what closes the gap: readable PII dropped from 36 to 1.
- **Known issue:** the verifier votes at `agreement_threshold=1`, so the
  MSER detector alone can flag ordinary text and blurred patches. Runs on
  text-heavy video therefore end `unresolved` even when almost no PII
  remains readable. The verifier should require a PII-aware signal (an OCR
  pattern or keyword match) before counting a span as still exposed.
- OCR found only 36 of 62 PII strings in the source video, so the
  before/after check measures what OCR can read, not every PII pixel.

### Limits

Synthetic data and classical CV detectors only. Faces and spoken PII are
not covered by this benchmark yet.


---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
