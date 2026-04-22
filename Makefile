PYTHON=python

.PHONY: install run-api run-dashboard test init-db seed-db init-db-with-seed generate-data ingest-data

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

run-api:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-dashboard:
	streamlit run dashboard/app.py

test:
	pytest -q

init-db:
	$(PYTHON) -m app.db.init_db --schema

seed-db:
	$(PYTHON) -m app.db.init_db --seed

init-db-with-seed:
	$(PYTHON) -m app.db.init_db --schema --seed

generate-data:
	$(PYTHON) -m app.experiments.synthetic_data --users 250 --days 60 --seed 42

ingest-data:
	$(PYTHON) -m app.db.ingest_events --users 250 --days 60 --seed 42
