.PHONY: install test eval doctor serve mcp
install:
	pip install -r requirements.txt && pip install -e .
test:
	pytest -q
eval:
	python evals/run_benchmark.py
doctor:
	infra-agent doctor
serve:
	infra-agent serve --port 8103
mcp:
	infra-agent mcp-serve
