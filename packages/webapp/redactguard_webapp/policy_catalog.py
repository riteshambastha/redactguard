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
from dataclasses import dataclass, field

from redactguard_core.pipeline.policy import PolicyProfile, load_policy

POLICIES_DIR = os.path.join(os.path.dirname(__file__), "policies")


@dataclass
class PolicyChoice:
    path: str
    profile: PolicyProfile


@dataclass
class PolicyDisplay:
    """Upload-form-only presentation for a policy - internal names like
    "demo_fast" are fine as the HTML form value and for filenames/logs,
    but meant nothing to a first-time visitor deciding what to pick (this
    was reported directly by a user looking at the upload page). Kept
    separate from `PolicyProfile` in redactguard-core rather than adding
    a `display_name` field there - this is presentation for one consumer
    of the pipeline, not a property of the policy itself, and a real
    compliance profile like gdpr_v1.yaml has no need for webapp copy.
    """

    title: str
    tagline: str
    badge_text: str
    badge_kind: str  # "offline" | "online" - selects the badge's CSS color
    details: list[str] = field(default_factory=list)


# Keyed by PolicyProfile.name. Anything not listed here (a custom policy
# someone drops into redactguard_webapp/policies/) still works - see
# `display_for()` below - it just falls back to the profile's own name
# and description rather than this curated copy.
_DISPLAY_INFO: dict[str, PolicyDisplay] = {
    "demo_fast": PolicyDisplay(
        title="Fast demo",
        tagline="Face + on-screen text, no downloads",
        badge_text="Works offline",
        badge_kind="offline",
        details=[
            "Detects faces and on-screen text (documents, screens, license plates)",
            "Every detector runs locally - no model downloads, no internet needed",
            "Best default if you just want to see RedactGuard work",
        ],
    ),
    "demo_with_audio": PolicyDisplay(
        title="Full demo, with audio",
        tagline="Adds spoken-PII detection in the audio track",
        badge_text="Downloads a model on first use",
        badge_kind="online",
        details=[
            "Everything in Fast demo, plus a real speech-to-text pass (faster-whisper)",
            (
                "Downloads Whisper model weights (~150MB) from Hugging Face Hub the first "
                "time this policy runs - needs internet access that one time, then it's cached"
            ),
            "Pick this if your video has spoken PII you want caught too",
        ],
    ),
}


def display_for(choice: PolicyChoice) -> PolicyDisplay:
    """The curated `PolicyDisplay` for a known demo policy, or a plain
    fallback built from the policy's own name/description for anything
    else - so a custom policy dropped into
    redactguard_webapp/policies/ renders reasonably without needing an
    entry here.
    """
    known = _DISPLAY_INFO.get(choice.profile.name)
    if known is not None:
        return known
    return PolicyDisplay(
        title=choice.profile.name.replace("_", " ").title(),
        tagline=choice.profile.description.strip() or "Custom policy",
        badge_text="Custom policy",
        badge_kind="offline",
        details=[],
    )


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
