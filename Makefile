# RedactGuard - developer Makefile
#
# Part of RedactGuard - a self-hosted, privacy-preserving video PII
# redaction toolkit with ensemble detection and a closed-loop
# verify-then-retry guardrail.
#
# Author: Ritesh Ambastha

.PHONY: install test lint typecheck docker webapp synth-data benchmark

install:
	pip install -e packages/core -e packages/cli -e packages/plugin-sdk -e packages/webapp
	pip install -e packages/plugin-sdk/examples/example_tattoo_detector_plugin
	pip install -r requirements-dev.txt

test:
	pytest packages/core/tests packages/cli/tests \
	    packages/plugin-sdk/examples/example_tattoo_detector_plugin/tests \
	    packages/webapp/tests -v

lint:
	ruff check packages

typecheck:
	mypy packages/core/redactguard_core packages/webapp/redactguard_webapp

docker:
	docker build -f docker/Dockerfile -t redactguard:cpu .

webapp:
	redactguard-webapp

synth-data:
	python -m synthetic.generator.scene_composer --out synthetic/datasets

benchmark:
	python benchmarks/run_benchmark.py

# ---------------------------------------------------------------------------
# RedactGuard - https://github.com/riteshambastha/redactguard
# Author: Ritesh Ambastha
# ---------------------------------------------------------------------------
