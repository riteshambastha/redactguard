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
CLI entrypoint

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

from __future__ import annotations

import logging

import click

from redactguard_cli.commands.batch import batch
from redactguard_cli.commands.run import run
from redactguard_cli.commands.scan import scan


@click.group()
@click.option("--quiet", is_flag=True, help="Suppress per-stage progress output (detect/redact/verify/retry).")
def cli(quiet: bool):
    """RedactGuard - self-hosted, privacy-preserving video PII redaction."""
    # Orchestrator.run()/scan() report every stage via logging.info() (see
    # docs/adr/0012) - a multi-minute `run` on a real video otherwise gives
    # no sign of life beyond "still going" until it either finishes or
    # crashes. Plain "%(message)s" so it reads like normal CLI output, not
    # a logging framework dump.
    if not quiet:
        logging.basicConfig(level=logging.INFO, format="%(message)s")


cli.add_command(scan)
cli.add_command(run)
cli.add_command(batch)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
