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
Detector registry and plugin discovery

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

from importlib.metadata import entry_points

from redactguard_core.detectors.base import AbstractDetector

_REGISTRY: dict[str, list[type[AbstractDetector]]] = {}

ENTRY_POINT_GROUP = "redactguard.detectors"


def register_detector(pii_type: str):
    """Class decorator: `@register_detector("face")` on an AbstractDetector
    subclass makes it discoverable for that PII type.
    """

    def _wrap(cls: type[AbstractDetector]) -> type[AbstractDetector]:
        _REGISTRY.setdefault(pii_type, []).append(cls)
        return cls

    return _wrap


_BUILTIN_MODULES = (
    "redactguard_core.detectors.face",
    "redactguard_core.detectors.text",
    "redactguard_core.detectors.audio",
)


def get_detectors(pii_type: str, policy=None) -> list[AbstractDetector]:
    """Instantiate every detector registered for a PII type, including
    built-in detectors that ship with core and third-party plugins
    discovered via the `redactguard.detectors` entry point group (see
    redactguard-plugin-sdk). If `policy` is given, each instance is
    configured with it via `AbstractDetector.configure()`.
    """
    _discover_builtin_detectors()
    _discover_plugins()
    instances = [cls() for cls in _REGISTRY.get(pii_type, [])]
    if policy is not None:
        for instance in instances:
            instance.configure(policy)
    return instances


def _discover_builtin_detectors() -> None:
    """Import each detectors/<pii_type> subpackage so its module-level
    @register_detector(...) decorators run. Cheap to call repeatedly -
    Python caches imports.
    """
    import importlib

    for module_name in _BUILTIN_MODULES:
        importlib.import_module(module_name)


def _discover_plugins() -> None:
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        ep.load()  # importing triggers the plugin's own @register_detector calls


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
