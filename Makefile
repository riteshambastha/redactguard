# RedactGuard - developer Makefile
#
# Part of RedactGuard - a self-hosted, privacy-preserving video PII
# redaction toolkit with ensemble detection and a closed-loop
# verify-then-retry guardrail.
#
# Author: Ritesh Ambastha

.PHONY: install test lint typecheck docker synth-data benchmark

install:
	pip install -e packages/core -e packages/cli -e packages/plugin-sdk
	pip install -r requirements-dev.txt

test:
	pytest packages/core/tests packages/cli/tests -v

lint:
	ruff check packages

typecheck:
	mypy packages/core/redactguard_core

docker:
	docker build -f docker/Dockerfile -t redactguard:cpu .

synth-data:
	python -m synthetic.generator.scene_composer --out synthetic/datasets

benchmark:
	python benchmarks/run_benchmark.py

# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
