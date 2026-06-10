# BALL — one-liners for the pipeline, app, and Docker services.
#
# Plain targets run natively (devcontainer / venv with requirements installed).
# docker-* targets run the same steps inside the shared image via compose —
# the SQLite DB lives on the ball-db volume, models on ball-artifacts.

.DEFAULT_GOAL := help
.PHONY: help install data features train evaluate explain pipeline app test lint \
        build up down docker-data docker-features docker-train docker-evaluate \
        docker-explain docker-pipeline notebook

help:  ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:  ## install pinned deps + the ball package (editable)
	pip install -r requirements-dev.txt && pip install -e .

# --- pipeline (native) ------------------------------------------------------
data:  ## bootstrap SQLite store from the sample CSVs
	python -m ball.pipeline.bootstrap

features:  ## build the X-day window dataset (+ Y-day targets)
	python -m ball.pipeline.features

train:  ## train per-forward-day LogReg + GradientBoosting (temporal split)
	python -m ball.pipeline.train

evaluate:  ## per-horizon ROC-AUC, verified against the frozen reference
	python -m ball.pipeline.evaluate

explain:  ## SHAP attribution for the day-7 GB model
	python -m ball.pipeline.explain

pipeline: data features train evaluate explain  ## full chain, end to end

app:  ## run the Streamlit dashboard natively
	streamlit run src/ball/app/app.py

test:  ## unit tests (incl. the temporal-split guard)
	python -m pytest tests/ -q

lint:  ## ruff over the production path
	ruff check .

# --- Docker -----------------------------------------------------------------
build:  ## build the shared image
	docker compose build

up:  ## start the dashboard at http://localhost:8501
	docker compose up --build app

down:  ## stop services (volumes survive)
	docker compose down

docker-data:  ## bootstrap the SQLite volume in-container
	docker compose run --rm pipeline python -m ball.pipeline.bootstrap

docker-features:  ## build the dataset in-container
	docker compose run --rm pipeline python -m ball.pipeline.features

docker-train:  ## train in-container
	docker compose run --rm pipeline python -m ball.pipeline.train

docker-evaluate:  ## evaluate in-container (reference check included)
	docker compose run --rm pipeline python -m ball.pipeline.evaluate

docker-explain:  ## SHAP in-container
	docker compose run --rm pipeline python -m ball.pipeline.explain

docker-pipeline:  ## full chain in one container run
	docker compose run --rm pipeline

notebook:  ## Jupyter Lab for the research notebooks at http://localhost:8888
	docker compose up --build notebook
