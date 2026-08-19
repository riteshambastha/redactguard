# Copyright 2026 Ritesh Ambastha
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Integration test: entry_points-based third-party plugin discovery

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from importlib.metadata import entry_points

from redactguard_core.detectors.registry import ENTRY_POINT_GROUP, get_detectors

# This test only proves anything if example-redactguard-tattoo-plugin - a
# real, separately-packaged, pip-installed distribution living at
# packages/plugin-sdk/examples/example_tattoo_detector_plugin - is
# installed in the current environment (part of `make install` and
# .github/workflows/ci.yml; see that package's README and docs/adr/0009).
# redactguard-core never imports it directly - if these tests pass, the
# plugin architecture (docs/adr/0004) genuinely works end-to-end, not
# just as a design sketch.


def test_example_plugin_entry_point_is_registered_in_this_environment():
    names = [ep.name for ep in entry_points(group=ENTRY_POINT_GROUP)]
    assert any("tattoo" in name for name in names), (
        "example-redactguard-tattoo-plugin isn't installed in this environment - "
        "run: pip install -e packages/plugin-sdk/examples/example_tattoo_detector_plugin"
    )


def test_get_detectors_loads_the_real_out_of_tree_plugin_class():
    detectors = get_detectors("tattoo")
    assert len(detectors) >= 1
    assert all(d.pii_type == "tattoo" for d in detectors)
    # Loaded by class name only, deliberately - this test file has no
    # import of example_redactguard_tattoo at all, so there's no way for
    # this assertion to pass except via the entry_points discovery path.
    assert any(type(d).__name__ == "TattooDetector" for d in detectors)


def test_scan_with_tattoo_enabled_runs_the_plugin_without_raising():
    # End-to-end through the same code path Orchestrator.scan() uses -
    # registry.run_detectors() - confirms the plugin is wired all the way
    # through, not just reachable via get_detectors() in isolation.
    from PIL import Image
    from redactguard_core.detectors.registry import run_detectors
    from redactguard_core.pipeline.ingest import DecodedMedia, Frame
    from redactguard_core.pipeline.policy import PiiTypeConfig, PolicyProfile

    policy = PolicyProfile(
        version=1,
        name="test-plugin-policy",
        pii_types={"tattoo": PiiTypeConfig(enabled=True)},
        agreement_threshold=1,
    )
    media = DecodedMedia(source_file="fake.mp4", frames=[Frame(timestamp_s=0.0, image=Image.new("RGB", (64, 64), "white"))])
    results = run_detectors(media, policy)  # would raise NotImplementedError if no detector were found
    assert results == []  # blank frame, nothing skin-toned to flag


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
