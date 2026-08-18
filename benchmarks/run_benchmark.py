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
Benchmark runner (skeleton)

Part of RedactGuard - a self-hosted, privacy-preserving video PII redaction
toolkit with ensemble detection and a closed-loop verify-then-retry guardrail.

Author: Ritesh Ambastha
"""

import argparse


def main() -> None:
    """Compute precision/recall/F1 per PII type against the synthetic and
    public benchmark sets.

    TODO: wire this up once detectors (walking-skeleton phase) and the
    synthetic generator exist. Skeleton only for now.
    """
    parser = argparse.ArgumentParser(description="RedactGuard benchmark runner")
    parser.add_argument("--dataset", default="synthetic/datasets", help="path to a benchmark dataset")
    args = parser.parse_args()
    raise NotImplementedError(
        f"Benchmarking against {args.dataset!r} is not wired up yet - "
        "needs real detectors and the synthetic generator first."
    )


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
