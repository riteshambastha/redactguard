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
`redactguard scan` command

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import click
from redactguard_core.pipeline.orchestrator import Orchestrator
from redactguard_core.pipeline.policy import load_policy


@click.command()
@click.argument("input_path")
@click.option("--policy", "policy_path", required=True, help="Path to a policy profile YAML, e.g. policies/gdpr_v1.yaml")
@click.option("--out", "manifest_out", default=None, help="Where to write the redaction manifest JSON")
def scan(input_path: str, policy_path: str, manifest_out: str | None):
    """Dry-run: detect PII and write a manifest. No video is modified."""
    policy = load_policy(policy_path)
    orchestrator = Orchestrator(policy)
    manifest = orchestrator.scan(input_path)
    out_path = manifest_out or f"{input_path}.manifest.json"
    manifest.to_json(out_path)
    click.echo(f"Wrote manifest to {out_path} ({len(manifest.spans)} spans)")


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
