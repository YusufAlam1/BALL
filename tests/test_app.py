"""Headless smoke test of the Streamlit app via streamlit.testing.

Needs the pipeline outputs (SQLite store + trained artifacts), so it skips
itself when they're absent — CI runs it after the pipeline smoke step.
"""
import pytest

from ball.pipeline import config

pytestmark = pytest.mark.skipif(
    not (config.db_path().exists() and (config.artifacts_dir() / "meta.json").exists()),
    reason="needs bootstrapped DB + trained artifacts (run `make pipeline` first)",
)


def test_app_renders_and_predicts():
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parents[1] / "src" / "ball" / "app" / "app.py"
    at = AppTest.from_file(str(app_path), default_timeout=180)
    at.run()
    assert not at.exception
    assert len(at.button) == 1 and len(at.text_input) == 1

    at.text_input[0].set_value("LeBron James")
    at.button[0].click()
    at.run()
    assert not at.exception
    assert not at.error
    assert at.success, "expected a successful prediction banner"
    assert len(at.dataframe) == 1  # the per-day probability table
