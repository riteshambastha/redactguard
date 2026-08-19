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
Policy profile discovery for the upload form

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha

Bundles its own demo policies (redactguard_webapp/policies/*.yaml) rather
than reaching into the monorepo's top-level policies/ directory, so this
package stays installable and runnable on its own, independent of the
repo layout it happens to live in during development (see ADR-0004/0009
on why plugins and this app both avoid assuming a specific on-disk
layout of the rest of the project). Named policy_catalog.py rather than
policies.py so it doesn't collide with the redactguard_webapp/policies/
data directory sitting right next to it.
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass

from redactguard_core.pipeline.policy import PolicyProfile, load_policy

POLICIES_DIR = os.path.join(os.path.dirname(__file__), "policies")


@dataclass
class PolicyChoice:
    path: str
    profile: PolicyProfile


def discover_policies(policies_dir: str = POLICIES_DIR) -> list[PolicyChoice]:
    """All *.yaml policy profiles in `policies_dir`, loaded and validated
    up front (so a broken policy file fails at app startup / test setup,
    not silently mid-upload), sorted by name for a stable dropdown order.
    """
    choices = [
        PolicyChoice(path=path, profile=load_policy(path))
        for path in sorted(glob.glob(os.path.join(policies_dir, "*.yaml")))
    ]
    return sorted(choices, key=lambda c: c.profile.name)


def find_policy(policies_dir: str, name: str) -> PolicyChoice | None:
    for choice in discover_policies(policies_dir):
        if choice.profile.name == name:
            return choice
    return None


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
