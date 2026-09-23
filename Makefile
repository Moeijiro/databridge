# Developer shortcuts. The README lists the raw commands too.

BACKEND := backend
VENV := $(BACKEND)/.venv/bin

.PHONY: help install api web seed test clean

help:
	@echo "make install  install backend + web dependencies"
	@echo "make api      run the API on :8000"
	@echo "make web      run the Next.js dashboard on :3000"
	@echo "make seed     (re)create the demo workspace (demo account, credentials, integrations and a week of runs)"
	@echo "make test     run the backend test suite"

install:
	python3 -m venv $(BACKEND)/.venv
	$(VENV)/pip install -r $(BACKEND)/requirements-dev.txt
	cd frontend && npm install

api:
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --port 8000

web:
	cd frontend && npm run dev

seed:
	cd $(BACKEND) && .venv/bin/python -m app.seed --reset

test:
	cd $(BACKEND) && .venv/bin/python -m pytest

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -f $(BACKEND)/*.db $(BACKEND)/*.db-wal $(BACKEND)/*.db-shm
