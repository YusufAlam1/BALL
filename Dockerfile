# BALL — shared base image for the pipeline, the Streamlit app, and the
# optional Jupyter service (see docker-compose.yml). Multi-stage: wheels are
# built in a throwaway builder so the runtime stays slim.
#
# Build:  docker build -t ball .
# Shell:  docker run --rm -it ball
# The pipeline reads the SQLite DB from $BALL_DB_PATH and writes models to
# $BALL_ARTIFACTS_DIR — both live on volumes, not in the image.

# --- builder: resolve and build all wheels --------------------------------
FROM python:3.12.11-slim-bookworm AS builder

# build-essential only as a fallback for any pin that lacks a wheel
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r /tmp/requirements.txt

# --- runtime ----------------------------------------------------------------
FROM python:3.12.11-slim-bookworm

# curl is used by the app service healthcheck in docker-compose.yml
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 ball

COPY requirements.txt /tmp/requirements.txt
RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    pip install --no-cache-dir --no-index --find-links=/wheels -r /tmp/requirements.txt

WORKDIR /app
COPY --chown=ball:ball pyproject.toml README.md ./
COPY --chown=ball:ball data ./data
COPY --chown=ball:ball src ./src

# Volume mount points for the SQLite DB and the trained-model artifacts
ENV BALL_DB_PATH=/data/BALL.db \
    BALL_ARTIFACTS_DIR=/artifacts \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1
RUN mkdir -p /data /artifacts && chown ball:ball /data /artifacts

USER ball

CMD ["bash"]
