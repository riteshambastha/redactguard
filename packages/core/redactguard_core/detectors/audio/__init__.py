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
audio detectors

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

# Importing this subpackage runs the @register_detector("audio") decorator
# in whisper_detector.py, below - see detectors/registry.py's
# _discover_builtin_detectors() for where this import is triggered.
from redactguard_core.detectors.audio.whisper_detector import WhisperAudioDetector  # noqa: F401


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
