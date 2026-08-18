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

import os
import subprocess

from redactguard_core.pipeline.ingest import has_audio_stream
from redactguard_core.pipeline.orchestrator import Orchestrator
from redactguard_core.pipeline.policy import PiiTypeConfig, PolicyProfile, RetryConfig

# agreement_threshold=1 mirrors policies/walking_skeleton_dev.yaml: none of
# the three built-in detectors have a second independent detector yet
# (ADR-0001), so requiring 2-detector agreement would drop every real
# detection in this walking-skeleton phase.
_POLICY = PolicyProfile(
    version=1,
    name="test-run-policy",
    pii_types={
        "text": PiiTypeConfig(enabled=True),
        "face": PiiTypeConfig(enabled=False),  # Haar cascade needs a real face image, not synthetic text video
        "audio": PiiTypeConfig(enabled=False),  # faster-whisper model download unavailable in this sandbox
    },
    agreement_threshold=1,
    retry=RetryConfig(max_attempts=2),
)


def _make_text_video(path: str, text: str = "SSN 123-45-6789 on file") -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=white:s=320x240:d=2",
            "-vf", f"drawtext=text='{text}':fontcolor=black:fontsize=20:x=10:y=100",
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
    # The original scan should have found the SSN text...
    assert len(report.manifest.spans) > 0
    assert report.manifest.spans[0].pii_type == "text"
    # ...and after redaction, the verifier should find it gone (blurred),
    # resolving without needing a single retry.
    assert report.unresolved is False
    assert len(report.verification_passes) == 1
    assert report.verification_passes[0].spans_still_flagged == 0


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


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
