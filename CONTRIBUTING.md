<!-- RedactGuard | Author: Ritesh Ambastha -->

# Contributing

RedactGuard is a young project maintained by Ritesh Ambastha. Issues and
PRs are welcome — please open an issue before a large PR so the design
direction can be agreed on first (see `docs/adr/` for the reasoning
behind existing decisions).

## Development setup

```bash
make install
make test
make lint
```

## Adding a detector

New detectors implement `AbstractDetector` from `redactguard-plugin-sdk`
and register via the `@register_detector("<pii_type>")` decorator, or via
a `redactguard.detectors` entry point for out-of-tree plugins. See
`packages/plugin-sdk/examples/example_tattoo_detector_plugin/README.md`.


---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
