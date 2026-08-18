<!-- RedactGuard | Author: Ritesh Ambastha -->

# Example: a third-party tattoo detector plugin

This is a design sketch, not yet a working example, of how an out-of-tree
detector plugin would be structured:

```
example-redactguard-tattoo/
├── pyproject.toml   # declares a [project.entry-points."redactguard.detectors"]
│                    # entry pointing at the class below
└── tattoo_detector.py
```

```python
from redactguard_plugin_sdk import AbstractDetector, DetectionResult, register_detector

@register_detector("tattoo")
class TattooDetector(AbstractDetector):
    name = "example-tattoo-detector"
    pii_type = "tattoo"

    def detect(self, media) -> list[DetectionResult]:
        ...
```

Installing `example-redactguard-tattoo` alongside RedactGuard is enough for
`detectors/registry.py`'s plugin discovery to pick it up automatically -
no core changes required. See docs/adr/0004-plugin-registry-for-detectors.md.


---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
