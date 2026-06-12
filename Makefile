# BALL — one-liners for the pipeline, app, and Docker services.
#
# Plain targets run natively (devcontainer / venv with requirements installed).
# docker-* targets run the same steps inside the shared image via compose —
# the SQLite DB lives on the ball-db volume, models on ball-artifacts.

.DEFAULT_GOAL := help
.PHONY: help install install-xgb data features train train-xgb tune-xgb evaluate explain \
        pipeline pipeline-xgb app test lint \
        build up down docker-data docker-features docker-train docker-evaluate \
        docker-explain docker-pipeline notebook \
        build-xgb up-xgb down-xgb docker-pipeline-xgb docker-tune-xgb

help:  ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:  ## install pinned deps + the ball package (editable)
	pip install -r requirements-dev.txt && pip install -e .

install-xgb:  ## install the optional XGBoost comparison dependency
	pip install -r requirements-xgb.txt

# --- pipeline (native) ------------------------------------------------------
data:  ## bootstrap SQLite store from the sample CSVs
	python -m ball.pipeline.bootstrap

features:  ## build the X-day window dataset (+ Y-day targets)
	python -m ball.pipeline.features

train:  ## train per-forward-day LogReg + GradientBoosting (temporal split)
	python -m ball.pipeline.train

train-xgb:  ## train LogReg + GradientBoosting + XGBoost for comparison (needs install-xgb)
	python -m ball.pipeline.train --model all

tune-xgb:  ## search XGBoost hyperparams on a temporal validation slice (test untouched)
	python -m ball.pipeline.tune_xgb

evaluate:  ## per-horizon ROC-AUC, verified against the frozen reference
	python -m ball.pipeline.evaluate

explain:  ## SHAP attribution for the day-7 GB model
	python -m ball.pipeline.explain

pipeline: data features train evaluate explain  ## full chain, end to end

pipeline-xgb: data features train-xgb evaluate explain  ## full chain incl. XGBoost comparison

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

# --- Docker (XGBoost variant: separate image/stack, see docker-compose.xgb.yml) ---
XGB_COMPOSE = docker compose -f docker-compose.xgb.yml

build-xgb:  ## build the XGBoost variant image
	$(XGB_COMPOSE) build

up-xgb:  ## start the XGBoost dashboard at http://localhost:8502
	$(XGB_COMPOSE) up --build app-xgb

down-xgb:  ## stop the XGBoost stack (ball-xgb-* volumes survive)
	$(XGB_COMPOSE) down

docker-pipeline-xgb:  ## full XGBoost comparison chain in one container run (--model all)
	$(XGB_COMPOSE) run --rm pipeline-xgb

docker-tune-xgb:  ## run the temporal-CV hyperparameter search in-container
	$(XGB_COMPOSE) run --rm tune-xgb
