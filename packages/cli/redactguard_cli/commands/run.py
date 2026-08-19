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
`redactguard run` command

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import click
from redactguard_core.pipeline.ingest import MediaDecodeError
from redactguard_core.pipeline.orchestrator import Orchestrator
from redactguard_core.pipeline.policy import load_policy


@click.command()
@click.argument("input_path")
@click.option("--policy", "policy_path", required=True, help="Path to a policy profile YAML")
@click.option("--out", "output_path", required=True, help="Redacted output file path")
def run(input_path: str, policy_path: str, output_path: str):
    """Apply redaction, verify, retry if needed, and write the output +
    audit report. See docs/adr/0002 for the retry/human-in-the-loop behavior.
    """
    policy = load_policy(policy_path)
    orchestrator = Orchestrator(policy)
    try:
        report = orchestrator.run(input_path, output_path)
    except MediaDecodeError as exc:
        # A corrupted/empty/unsupported input file otherwise surfaces as a
        # raw ffmpeg subprocess traceback - see docs/adr/0014. ClickException
        # prints "Error: ..." to stderr and exits 1, same as any other
        # click-level usage error.
        raise click.ClickException(str(exc)) from exc
    if report.unresolved:
        click.echo(click.style("UNRESOLVED - see audit report for human review", fg="red", bold=True))
    click.echo(report.render_markdown())


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
