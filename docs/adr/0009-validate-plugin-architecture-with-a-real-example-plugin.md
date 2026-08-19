<!-- RedactGuard | Author: Ritesh Ambastha -->

# 0009. Validate the plugin architecture with a real, installed example plugin

- Status: Accepted
- Author: Ritesh Ambastha

## Context

ADR-0004 designed `detectors/registry.py`'s `redactguard.detectors`
entry-point group so third parties could ship detectors as independent
pip packages, with zero changes to `redactguard-core`. Until now, that
was entirely unverified: `packages/plugin-sdk/examples/` held a README
labeled "a design sketch, not yet a working example," and there was no
test anywhere exercising `_discover_plugins()` or `entry_points()` at
all. A design that's only ever been imagined, never actually installed
and loaded, is exactly the kind of thing that looks right on paper and
breaks on first real use (wrong entry-point value format, a class that
doesn't actually satisfy `AbstractDetector`, a packaging mistake) - which
is a real risk for a feature this project's pitch leans on.

## Decision

Turn the tattoo-detector sketch into a real, separately-packaged,
pip-installable distribution (`example-redactguard-tattoo-plugin`,
under `packages/plugin-sdk/examples/example_tattoo_detector_plugin/`)
with its own `pyproject.toml` declaring a real
`[project.entry-points."redactguard.detectors"]` entry, a real detector
implementation, and its own unit tests. `redactguard-core` never imports
this package directly - anywhere.

`packages/core/tests/test_plugin_discovery.py` installs alongside it (via
`make install` / CI) and asserts, from the core package's side, that:
the entry point is visible via `importlib.metadata.entry_points()`;
`get_detectors("tattoo")` returns a real `TattooDetector` instance loaded
purely through that mechanism; and `run_detectors()` (the same function
`Orchestrator.scan()` and `Verifier.verify()` use) runs it without
raising, end-to-end. If these tests pass, the plugin architecture works
for a genuine out-of-tree package, not just as a paper design.

The example detector itself (HSV skin-tone thresholding + local
pixel-variance heuristic, flagging patches of unusually high local
contrast within skin-toned regions) is intentionally a toy: real tattoo
detection needs a trained model, and pretending otherwise would undercut
the "detectors are honestly documented, not oversold" standard the rest
of this project holds to. It's real enough to have actual true/false
behavior worth testing (a plain skin-toned frame produces zero
detections; a noisy patch on skin is flagged; the same noisy patch on a
non-skin background is correctly suppressed by the skin-tone gate), which
is what makes it useful as a plugin-wiring proof rather than a decorative
stub.

## Consequences

The plugin architecture is now something this project has actually run,
not just designed. `.github/workflows/ci.yml` and the `Makefile` both
install and test the example plugin as a standing part of every CI run,
so a future change to `detectors/registry.py` that breaks entry-point
discovery would be caught immediately rather than discovered by the first
real third-party plugin author.

One real limitation surfaced in writing this: the entry-point *name*
(the left-hand side of `example-tattoo-detector = "..."` in
`pyproject.toml`) is cosmetic - `_discover_plugins()` only calls
`ep.load()` on it; the actual `pii_type` mapping comes from the
`@register_detector("tattoo")` decorator on the class itself. That's a
one-line fact worth documenting for future plugin authors (and now is,
here and in the example package's README) rather than something they'd
have to discover by reading `registry.py`.

---
*RedactGuard — maintained by Ritesh Ambastha ([@riteshambastha](https://github.com/riteshambastha))*
