<!-- RedactGuard | Author: Ritesh Ambastha -->

# Example: a real, working third-party tattoo detector plugin

This used to be a design sketch. It's now a real, installable, out-of-tree
package (`example-redactguard-tattoo-plugin`) that RedactGuard's core never
imports or references directly - it's discovered purely through the
`redactguard.detectors` entry-point group, the same mechanism any real
third-party plugin would use. `packages/core/tests/test_plugin_discovery.py`
installs it (via `make install` / CI, see `.github/workflows/ci.yml`) and
proves the discovery path actually works end-to-end - see docs/adr/0009.

```
example_tattoo_detector_plugin/
├── pyproject.toml                        # declares [project.entry-points."redactguard.detectors"]
├── example_redactguard_tattoo/
│   ├── __init__.py                       # exports TattooDetector
│   └── detector.py                       # the actual detector
└── tests/
    └── test_tattoo_detector.py           # unit tests for the detector's own heuristic
```

```python
from redactguard_plugin_sdk import AbstractDetector, DetectionResult, register_detector

@register_detector("tattoo")
class TattooDetector(AbstractDetector):
    name = "example-skin-variance-heuristic"
    pii_type = "tattoo"

    def detect(self, media) -> list[DetectionResult]:
        ...  # skin-tone + local-variance heuristic - see detector.py's docstring
```

Installing this package alongside RedactGuard (`pip install -e
packages/plugin-sdk/examples/example_tattoo_detector_plugin`) is enough for
`redactguard_core/detectors/registry.py`'s plugin discovery to pick it up
automatically at runtime - no core changes required. Enable it via a
policy's `pii_types.tattoo.enabled: true` and it participates in
scan/run/verify exactly like a built-in detector.

**This is a wiring example, not a production detector.** The actual
tattoo-detection heuristic (HSV skin-tone thresholding + local pixel
variance) is intentionally crude - see `detector.py`'s docstring for its
honest limitations. Anyone building a real third-party plugin should copy
the packaging/entry-point structure here, not the detection logic.

See `docs/adr/0004-plugin-registry-for-detectors.md` for why the plugin
architecture exists, and `docs/adr/0009` for what building and testing a
real one against it turned up.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
