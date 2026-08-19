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

import os

import click
from redactguard_core.pipeline.ingest import iter_input_paths
from redactguard_core.pipeline.orchestrator import Orchestrator
from redactguard_core.pipeline.policy import load_policy


@click.command()
@click.argument("input_dir")
@click.option("--policy", "policy_path", required=True, help="Path to a policy profile YAML")
@click.option("--out-dir", "output_dir", required=True, help="Directory for redacted outputs + reports")
def batch(input_dir: str, policy_path: str, output_dir: str):
    """Process every video under a folder/archive in one invocation,
    aggregating per-file reports. Each file gets its own Orchestrator.run()
    (see docs/adr/0002) - one file's retry loop or failure never blocks the
    rest of the batch; unresolved files are flagged in the summary for
    human review rather than halting the run.
    """
    paths = list(iter_input_paths(input_dir))
    click.echo(f"Found {len(paths)} video file(s) under {input_dir}")
    os.makedirs(output_dir, exist_ok=True)
    policy = load_policy(policy_path)

    unresolved_count = 0
    failed_count = 0
    for path in paths:
        base = os.path.splitext(os.path.basename(path))[0]
        out_path = os.path.join(output_dir, f"{base}.redacted.mp4")
        report_path = os.path.join(output_dir, f"{base}.report.md")
        click.echo(f"  - {path} -> {out_path}")

        try:
            report = Orchestrator(policy).run(path, out_path)
        except Exception as exc:  # noqa: BLE001 - intentionally blind: one corrupted/
            # unreadable file in a folder must not abort every other file's
            # redaction, per this command's own docstring - see docs/adr/0014.
            failed_count += 1
            with open(report_path, "w") as f:
                f.write(f"# {base} - FAILED\n\n{exc}\n")
            click.echo(click.style(f"    FAILED - {exc}", fg="red"))
            continue

        with open(report_path, "w") as f:
            f.write(report.render_markdown())

        if report.unresolved:
            unresolved_count += 1
            click.echo(click.style(f"    UNRESOLVED - see {report_path}", fg="red"))

    click.echo(
        f"\nDone: {len(paths)} file(s), {unresolved_count} unresolved, "
        f"{failed_count} failed (see reports in {output_dir})"
    )
    if unresolved_count or failed_count:
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
