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
CLI smoke tests

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

import logging
import subprocess

from click.testing import CliRunner
from redactguard_cli.main import cli


def test_cli_help():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.output
    assert "run" in result.output
    assert "batch" in result.output


def _make_text_video(path: str) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=white:s=320x240:d=2",
            "-vf", "drawtext=text='SSN 123-45-6789 on file':fontcolor=black:fontsize=20:x=10:y=100",
            "-r", "4", path,
        ],
        capture_output=True, check=True,
    )


def test_scan_prints_progress_by_default(tmp_path):
    # See docs/adr/0012 - `cli()`'s group callback turns on INFO logging
    # unless --quiet is passed, so a real scan should show stage-by-stage
    # progress on stdout/stderr, not just the final summary line.
    source = str(tmp_path / "source.mp4")
    _make_text_video(source)
    manifest_out = str(tmp_path / "manifest.json")

    # logging.basicConfig() is a process-wide no-op after the first call in
    # this test process, so reset any handler a prior test/import may have
    # installed to make sure this invocation's own basicConfig call takes
    # effect and its output is actually captured.
    logging.getLogger().handlers.clear()

    result = CliRunner().invoke(
        cli, ["scan", source, "--policy", "policies/walking_skeleton_dev.yaml", "--out", manifest_out]
    )
    assert result.exit_code == 0, result.output
    assert "detector ensemble" in result.output
    assert "Scan complete" in result.output


def test_scan_quiet_suppresses_progress_output(tmp_path):
    source = str(tmp_path / "source.mp4")
    _make_text_video(source)
    manifest_out = str(tmp_path / "manifest.json")

    logging.getLogger().handlers.clear()

    result = CliRunner().invoke(
        cli, ["--quiet", "scan", source, "--policy", "policies/walking_skeleton_dev.yaml", "--out", manifest_out]
    )
    assert result.exit_code == 0, result.output
    assert "detector ensemble" not in result.output
    assert "Wrote manifest to" in result.output  # the command's own summary line still prints


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
