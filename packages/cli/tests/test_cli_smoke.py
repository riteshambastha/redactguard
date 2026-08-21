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
import os
import subprocess

from click.testing import CliRunner
from redactguard_cli.main import cli


def test_cli_help():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.output
    assert "run" in result.output
    assert "batch" in result.output


# fontfile= is required, not cosmetic: without it, ffmpeg's drawtext
# filter resolves fonts by *family name* through fontconfig, which
# silently depends on some font file existing wherever this test runs -
# true on a dev machine, not guaranteed on a minimal CI/container image.
# Pinned to the package CI now installs explicitly (fonts-dejavu-core) -
# see docs/adr/0017, which found this exact gap breaking docker-build's
# smoke test the same way it could have broken this fixture.
_DEJAVU_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _make_text_video(path: str) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=white:s=320x240:d=2",
            "-vf", f"drawtext=fontfile={_DEJAVU_SANS}:text='SSN 123-45-6789 on file':fontcolor=black:fontsize=20:x=10:y=100",
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


def _make_corrupted_file(path: str) -> None:
    with open(path, "wb") as f:
        f.write(b"not a real video file, just some bytes")


def test_scan_on_a_corrupted_file_prints_a_clean_error_not_a_traceback(tmp_path):
    # See docs/adr/0014 - before this, a corrupted/unsupported input made
    # it all the way to an unhandled subprocess.CalledProcessError and a
    # raw Python traceback on stderr.
    bad_source = str(tmp_path / "corrupted.mp4")
    _make_corrupted_file(bad_source)

    result = CliRunner().invoke(
        cli, ["scan", bad_source, "--policy", "policies/walking_skeleton_dev.yaml"]
    )
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "Error:" in result.output


def test_run_on_a_corrupted_file_prints_a_clean_error_not_a_traceback(tmp_path):
    bad_source = str(tmp_path / "corrupted.mp4")
    _make_corrupted_file(bad_source)
    output = str(tmp_path / "output.mp4")

    result = CliRunner().invoke(
        cli, ["run", bad_source, "--policy", "policies/walking_skeleton_dev.yaml", "--out", output]
    )
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "Error:" in result.output
    assert not os.path.exists(output)


def test_batch_processes_remaining_files_after_one_corrupted_file(tmp_path):
    # The batch command's own docstring claims "one file's retry loop or
    # failure never blocks the rest of the batch" - this pins that down
    # with a real corrupted file sitting alongside a real valid one.
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    _make_corrupted_file(str(input_dir / "a_corrupted.mp4"))
    _make_text_video(str(input_dir / "b_valid.mp4"))
    output_dir = tmp_path / "outputs"

    result = CliRunner().invoke(
        cli,
        ["batch", str(input_dir), "--policy", "policies/walking_skeleton_dev.yaml", "--out-dir", str(output_dir)],
    )

    assert "1 failed" in result.output
    assert os.path.exists(output_dir / "a_corrupted.report.md")
    assert "FAILED" in (output_dir / "a_corrupted.report.md").read_text()
    # The valid file after the corrupted one must still have been processed.
    assert os.path.exists(output_dir / "b_valid.redacted.mp4")
    assert os.path.getsize(output_dir / "b_valid.redacted.mp4") > 0
    assert os.path.exists(output_dir / "b_valid.report.md")
    assert result.exit_code != 0  # a batch with any failure still signals non-zero


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
