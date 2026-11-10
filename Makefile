.PHONY: setup run test eval eval-dry
setup:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
run:
	uvicorn app.main:app --reload --port 8000
test:
	python -m pytest -q
eval-dry:
	python -m eval.run_eval --dry-run
eval:
	python -m eval.run_eval
