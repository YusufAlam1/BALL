"""Pipeline configuration: paths come from the environment so the same code runs
locally (repo-relative defaults) and in Docker (volume mounts)."""
import os
from pathlib import Path

# v2 defaults: X = 14-day lookback, Y = 14-day forward horizon
DEFAULT_LOOKBACK_DAYS = 14
DEFAULT_FORWARD_DAYS = 14
RANDOM_STATE = 42
TRAIN_FRACTION = 0.8  # temporal split: earliest 80% of observation dates train

# Repo root when running from a source checkout or the Docker image
# (config.py -> pipeline -> ball -> src -> root).
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Sample data shipped in the repo/image: one 2015-16 season.
SAMPLE_MODEL_INPUT_CSV = (
    _REPO_ROOT / "src" / "ball" / "models" / "injury_prediction" / "v2" / "model_input_file.csv"
)
SAMPLE_GAME_DATES_CSV = _REPO_ROOT / "data" / "1-nba_api" / "game_dates.csv"
SAMPLE_PLAYERS_CSV = _REPO_ROOT / "data" / "1-nba_api" / "players.csv"

# Frozen reference numbers the extracted pipeline must reproduce.
REFERENCE_RESULTS_CSV = Path(__file__).resolve().parent / "reference" / "v2_results_2015-16.csv"


def db_path() -> Path:
    """SQLite store. In Docker this is /data/BALL.db on the db volume."""
    return Path(os.environ.get("BALL_DB_PATH", str(_REPO_ROOT / "data" / "BALL.db")))


def artifacts_dir() -> Path:
    """Trained models / datasets / reports. In Docker: /artifacts volume."""
    d = Path(os.environ.get("BALL_ARTIFACTS_DIR", str(_REPO_ROOT / "artifacts")))
    d.mkdir(parents=True, exist_ok=True)
    return d


def dataset_path() -> Path:
    return artifacts_dir() / "dataset.csv"
