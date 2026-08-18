<!-- RedactGuard | Author: Ritesh Ambastha -->

# Threat model & known limitations

RedactGuard reduces the risk of PII leaking through video, but it is a
detection system, not a proof system. Known, documented limitations:

- **Detectors are probabilistic.** Ensemble voting (ADR-0001) reduces,
  but does not eliminate, false negatives — a person facing away from
  camera, extreme motion blur, or unusual lighting can still slip past
  every detector in the ensemble.
- **The verify-then-retry loop is bounded.** After `retry.max_attempts`
  escalations, if PII is still flagged, RedactGuard emits the output
  anyway with a loud "unresolved" warning (ADR-0002) rather than
  withholding the file — this is a deliberate human-in-the-loop choice,
  not a guarantee of full redaction.
- **OCR/text coverage is limited by the chosen models' language support.**
  Text in unsupported scripts/languages may not be detected.
- **Custom keyword matching is string/fuzzy-match based**, not semantic —
  paraphrases or synonyms of a flagged term will not be caught.
- **Audio PII detection is bounded by ASR + Presidio's supported entity
  types and languages.** Uncommon PII formats or low-resource languages
  are more likely to be missed.
- **This is not a formally verified system.** No cryptographic or formal
  guarantee is made that all PII has been removed; treat the audit report
  as an aid to human review, not a certification.


---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
