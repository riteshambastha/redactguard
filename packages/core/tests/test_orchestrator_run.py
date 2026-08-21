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
End-to-end tests for Orchestrator.run() - the full detect -> redact ->
verify -> retry -> report closed loop, against real ffmpeg-generated video.

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

import glob
import os
import subprocess
import tempfile

import pytest
from redactguard_core.pipeline.ingest import MediaDecodeError, has_audio_stream
from redactguard_core.pipeline.orchestrator import Orchestrator
from redactguard_core.pipeline.policy import PiiTypeConfig, PolicyProfile, RetryConfig


def _redactguard_tempdirs() -> set[str]:
    """Every tempdir the pipeline itself creates is prefixed
    "redactguard-" (ingest.decode_media, and Orchestrator.run()'s own
    native-frames/attempt-scratch dirs) - see docs/adr/0014. Used to
    assert none are left behind after a run.
    """
    return set(glob.glob(os.path.join(tempfile.gettempdir(), "redactguard-*")))

# agreement_threshold=2 mirrors the real profiles (policies/gdpr_v1.yaml
# etc.) now that text has two independent detectors (Tesseract OCR + MSER
# structural region proposal - see docs/adr/0008). Note that Tesseract's
# word-level OCR bbox and MSER's finer sub-word regions don't always
# spatially overlap enough to agree on the *first* pass over real text -
# ADR-0008 documents why, and why the retry/escalation loop (which
# progressively lowers the threshold) is what makes that non-fatal rather
# than a design bug; max_attempts=3 gives it room to actually converge.
_POLICY = PolicyProfile(
    version=1,
    name="test-run-policy",
    pii_types={
        "text": PiiTypeConfig(enabled=True),
        "face": PiiTypeConfig(enabled=False),  # Haar/LBP cascades need a real face image, not synthetic text video
        "audio": PiiTypeConfig(enabled=False),  # faster-whisper model download unavailable in this sandbox
    },
    agreement_threshold=2,
    retry=RetryConfig(max_attempts=3),
)


# fontfile= pinned rather than left to fontconfig's family-name lookup -
# see docs/adr/0017, which found this exact drawtext pattern with no
# fontfile= breaking a CI job outright when no font happened to be
# installed in that environment.
_DEJAVU_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _make_text_video(path: str, text: str = "SSN 123-45-6789 on file") -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=white:s=320x240:d=2",
            "-vf", f"drawtext=fontfile={_DEJAVU_SANS}:text='{text}':fontcolor=black:fontsize=20:x=10:y=100",
            "-r", "4", path,
        ],
        capture_output=True, check=True,
    )


def test_run_redacts_burned_in_text_and_resolves_clean(tmp_path):
    source = str(tmp_path / "source.mp4")
    _make_text_video(source)
    output = str(tmp_path / "output.mp4")

    report = Orchestrator(_POLICY, sample_fps=2.0).run(source, output)

    assert os.path.exists(output)
    assert os.path.getsize(output) > 0
    assert all(s.pii_type == "text" for s in report.manifest.spans)
    # The closed loop should converge to a clean redaction within
    # max_attempts - it never withholds output, and the *last* verification
    # pass should find nothing left, whether that took one attempt or
    # needed the retry escalation to get there (see the _POLICY comment).
    assert report.unresolved is False
    assert len(report.verification_passes) >= 1
    assert report.verification_passes[-1].spans_still_flagged == 0


def test_run_on_clean_video_produces_no_spans_and_resolves(tmp_path):
    source = str(tmp_path / "clean.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=white:s=320x240:d=1", "-r", "2", source],
        capture_output=True, check=True,
    )
    output = str(tmp_path / "output.mp4")

    report = Orchestrator(_POLICY, sample_fps=2.0).run(source, output)

    assert os.path.exists(output)
    assert report.manifest.spans == []
    assert report.unresolved is False


def test_run_preserves_native_frame_rate_in_output(tmp_path):
    source = str(tmp_path / "source.mp4")
    _make_text_video(source)
    output = str(tmp_path / "output.mp4")

    Orchestrator(_POLICY, sample_fps=2.0).run(source, output)

    from redactguard_core.pipeline.ingest import get_frame_rate
    assert get_frame_rate(output) == get_frame_rate(source)


def test_run_with_silent_source_produces_video_with_no_audio_stream(tmp_path):
    source = str(tmp_path / "source.mp4")
    _make_text_video(source)
    output = str(tmp_path / "output.mp4")

    Orchestrator(_POLICY, sample_fps=2.0).run(source, output)

    assert has_audio_stream(output) is False


def test_run_reports_progress_through_on_progress_callback(tmp_path):
    # See docs/adr/0012 - this is what lets a caller (e.g. redactguard-webapp)
    # show live stage-by-stage progress instead of a static "running" label.
    source = str(tmp_path / "source.mp4")
    _make_text_video(source)
    output = str(tmp_path / "output.mp4")

    messages: list[str] = []
    Orchestrator(_POLICY, sample_fps=2.0, on_progress=messages.append).run(source, output)

    assert any("Decoding" in m for m in messages)
    assert any("detector ensemble" in m for m in messages)
    assert any("voting" in m for m in messages)
    assert any("redacting" in m for m in messages)
    assert any("verif" in m for m in messages)
    # The final message for a run that resolves cleanly should say so.
    assert any("verification clean" in m for m in messages)


def test_run_reports_progress_via_logging_even_without_a_callback(tmp_path, caplog):
    import logging

    source = str(tmp_path / "source.mp4")
    _make_text_video(source)
    output = str(tmp_path / "output.mp4")

    with caplog.at_level(logging.INFO, logger="redactguard_core.pipeline.orchestrator"):
        Orchestrator(_POLICY, sample_fps=2.0).run(source, output)

    assert any("Decoding" in record.message for record in caplog.records)


def test_scan_also_reports_progress(tmp_path):
    source = str(tmp_path / "source.mp4")
    _make_text_video(source)

    messages: list[str] = []
    Orchestrator(_POLICY, sample_fps=2.0, on_progress=messages.append).scan(source)

    assert any("Scan complete" in m for m in messages)


def test_run_leaves_no_temp_directories_behind_on_success(tmp_path):
    # See docs/adr/0014 - before this, every run() call (the source
    # decode, the native-fps redaction frames, the per-attempt scratch
    # dir, and one more per verify-retry attempt) leaked a tempdir for
    # the life of the process.
    source = str(tmp_path / "source.mp4")
    _make_text_video(source)
    output = str(tmp_path / "output.mp4")

    before = _redactguard_tempdirs()
    Orchestrator(_POLICY, sample_fps=2.0).run(source, output)
    after = _redactguard_tempdirs()

    assert after == before, f"run() leaked tempdir(s): {after - before}"


def test_scan_leaves_no_temp_directories_behind(tmp_path):
    source = str(tmp_path / "source.mp4")
    _make_text_video(source)

    before = _redactguard_tempdirs()
    Orchestrator(_POLICY, sample_fps=2.0).scan(source)
    after = _redactguard_tempdirs()

    assert after == before, f"scan() leaked tempdir(s): {after - before}"


def test_run_leaves_no_temp_directories_behind_even_when_it_raises(tmp_path):
    # A corrupted source fails inside decode_media() partway through
    # run() - the tempdirs created before the failure (the source
    # decode's own workdir, in this case) must still be cleaned up by the
    # `finally` in Orchestrator.run(), not just on the success path.
    bad_source = str(tmp_path / "corrupted.mp4")
    with open(bad_source, "wb") as f:
        f.write(b"not a real video file")
    output = str(tmp_path / "output.mp4")

    before = _redactguard_tempdirs()
    with pytest.raises(MediaDecodeError):
        Orchestrator(_POLICY, sample_fps=2.0).run(bad_source, output)
    after = _redactguard_tempdirs()

    assert after == before, f"run() leaked tempdir(s) on its failure path: {after - before}"
    assert not os.path.exists(output)


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
