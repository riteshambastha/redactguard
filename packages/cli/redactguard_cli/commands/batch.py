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
`redactguard batch` command

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import click
from redactguard_core.pipeline.ingest import iter_input_paths


@click.command()
@click.argument("input_dir")
@click.option("--policy", "policy_path", required=True, help="Path to a policy profile YAML")
@click.option("--out-dir", "output_dir", required=True, help="Directory for redacted outputs + reports")
def batch(input_dir: str, policy_path: str, output_dir: str):
    """Process every video under a folder/archive in one invocation,
    aggregating per-file reports.
    """
    paths = list(iter_input_paths(input_dir))
    click.echo(f"Found {len(paths)} video file(s) under {input_dir}")
    for path in paths:
        click.echo(f"  - {path}")
    raise NotImplementedError(
        "Per-file batch execution lands once Orchestrator.run() is wired up "
        "(walking-skeleton phase and beyond)."
    )


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
