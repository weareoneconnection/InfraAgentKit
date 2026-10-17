run:
	./run.sh

test:
	PYTHONPATH=. pytest -q

eval:
	PYTHONPATH=. python evals/run_benchmark.py

doctor:
	PYTHONPATH=. python -m infraagentkit.cli doctor
