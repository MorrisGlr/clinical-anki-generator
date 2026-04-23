"""Tests for the HEART Flask web UI (heart/server/app.py)."""
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from heart.server.app import _RUNS, create_app


@pytest.fixture()
def app(tmp_path):
    """Flask app configured to write output to a temp directory."""
    application = create_app(output_dir=tmp_path / "gen_anki")
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


# ── Index page ────────────────────────────────────────────────────────────────


def test_index_redirects_to_setup_without_key(client):
    with patch.dict("os.environ", {}, clear=True):
        resp = client.get("/")
    assert resp.status_code == 302
    assert "/setup" in resp.headers["Location"]


def test_index_returns_200_with_key(client):
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        resp = client.get("/")
    assert resp.status_code == 200
    assert b"Generate" in resp.data


# ── Setup page ────────────────────────────────────────────────────────────────


def test_setup_get_returns_200(client):
    resp = client.get("/setup")
    assert resp.status_code == 200
    assert b"API Key" in resp.data


def test_setup_post_saves_key_and_redirects(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("heart.server.app.set_key") as mock_set, \
         patch("heart.server.app.load_dotenv"):
        resp = client.post("/setup", data={"api_key": "sk-abc123"})
    mock_set.assert_called_once_with(str(Path(".env")), "OPENAI_API_KEY", "sk-abc123")
    assert resp.status_code == 302
    assert "/" in resp.headers["Location"]


def test_setup_post_empty_key_still_redirects(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("heart.server.app.set_key") as mock_set, \
         patch("heart.server.app.load_dotenv"):
        resp = client.post("/setup", data={"api_key": ""})
    mock_set.assert_not_called()
    assert resp.status_code == 302


# ── Run endpoint ──────────────────────────────────────────────────────────────


def test_run_no_files_returns_error(client):
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        resp = client.post("/run", data={"platform": "uworld"}, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert b"select at least one file" in resp.data


def test_run_redirects_to_progress(client, tmp_path):
    """POST /run with a valid file starts pipeline thread and redirects."""
    html_content = b"<html><body>test</body></html>"
    dummy_file = (io.BytesIO(html_content), "question_1.html")

    with patch("heart.server.app.threading.Thread") as mock_thread_cls, \
         patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread
        resp = client.post(
            "/run",
            data={"platform": "uworld", "files": dummy_file},
            content_type="multipart/form-data",
        )

    assert resp.status_code == 302
    assert "/progress/" in resp.headers["Location"]
    mock_thread.start.assert_called_once()


# ── Progress page ─────────────────────────────────────────────────────────────


def test_progress_page_returns_200_for_known_run(client, tmp_path):
    run_id = "2026-01-01_00-00-00"
    _make_run(run_id, tmp_path / "out.txt")
    _RUNS[run_id]["status"] = "running"
    try:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            resp = client.get(f"/progress/{run_id}")
        assert resp.status_code == 200
        assert run_id.encode() in resp.data
    finally:
        _RUNS.pop(run_id, None)


def test_progress_page_redirects_for_unknown_run(client):
    resp = client.get("/progress/nonexistent-run-id")
    assert resp.status_code == 302
    assert "/" in resp.headers["Location"]


# ── Download endpoint ─────────────────────────────────────────────────────────


def _make_run(run_id, output_path, platform="uworld", cards=None, summary=None):
    """Helper: insert a fully-structured run entry into _RUNS."""
    from queue import Queue
    _RUNS[run_id] = {
        "queue": Queue(),
        "output_path": output_path,
        "status": "done",
        "platform": platform,
        "anki_media_path": None,
        "cards": cards or [],
        "summary": summary,
    }


def test_download_returns_file(client, tmp_path):
    output_file = tmp_path / "gen_anki" / "2026-01-01_00-00-00.txt"
    output_file.parent.mkdir(parents=True)
    output_file.write_text("front\tback\n", encoding="utf-8")

    run_id = "2026-01-01_00-00-00"
    _make_run(run_id, output_file)
    try:
        resp = client.get(f"/download/{run_id}")
        assert resp.status_code == 200
        assert b"front\tback" in resp.data
    finally:
        _RUNS.pop(run_id, None)


def test_download_404_for_unknown_run(client):
    resp = client.get("/download/no-such-run")
    assert resp.status_code == 404


def test_download_404_when_file_missing(client, tmp_path):
    run_id = "2026-01-01_12-00-00"
    _make_run(run_id, tmp_path / "nonexistent.txt")
    try:
        resp = client.get(f"/download/{run_id}")
        assert resp.status_code == 404
    finally:
        _RUNS.pop(run_id, None)


# ── Results page ──────────────────────────────────────────────────────────────


def test_results_page_returns_200_for_known_run(client, tmp_path):
    run_id = "2026-06-01_10-00-00"
    cards = [
        {"n": 1, "front": "What is X?", "back": "X is Y.", "flagged": False, "cost_usd": 0.001},
        {"n": 2, "front": "What is Z?", "back": "Z is W.", "flagged": True,  "cost_usd": 0.002},
    ]
    summary = {"total": 2, "skipped": 0, "cost_usd": 0.003}
    _make_run(run_id, tmp_path / "out.txt", cards=cards, summary=summary)
    try:
        resp = client.get(f"/results/{run_id}")
        assert resp.status_code == 200
        assert b"What is X?" in resp.data
        assert b"Flagged for review" in resp.data
    finally:
        _RUNS.pop(run_id, None)


def test_results_page_redirects_for_unknown_run(client):
    resp = client.get("/results/nonexistent-run-id")
    assert resp.status_code == 302
    assert "/" in resp.headers["Location"]


def test_results_page_shows_uworld_copy_button(client, tmp_path):
    run_id = "2026-06-01_11-00-00"
    _make_run(run_id, tmp_path / "out.txt", platform="uworld")
    try:
        resp = client.get(f"/results/{run_id}")
        assert b"copy-media-btn" in resp.data
    finally:
        _RUNS.pop(run_id, None)


def test_results_page_hides_copy_button_for_nbme(client, tmp_path):
    run_id = "2026-06-01_12-00-00"
    _make_run(run_id, tmp_path / "out.txt", platform="nbme")
    try:
        resp = client.get(f"/results/{run_id}")
        assert b"copy-media-btn" not in resp.data
    finally:
        _RUNS.pop(run_id, None)


# ── Copy media endpoint ───────────────────────────────────────────────────────


def test_copy_media_returns_404_for_unknown_run(client):
    resp = client.post("/copy-media/no-such-run")
    assert resp.status_code == 404


def test_copy_media_calls_copy_media_fn(client, tmp_path):
    # Set up a run with a real output path and a fake anki media dir
    anki_dir = tmp_path / "anki_media"
    anki_dir.mkdir()
    output_file = tmp_path / "out.txt"
    output_file.write_text("", encoding="utf-8")

    run_id = "2026-06-01_13-00-00"
    from queue import Queue
    _RUNS[run_id] = {
        "queue": Queue(),
        "output_path": output_file,
        "status": "done",
        "platform": "uworld",
        "anki_media_path": str(anki_dir),
        "cards": [],
        "summary": None,
    }
    try:
        with patch("heart.server.app.copy_media", return_value=[]) as mock_copy:
            resp = client.post(f"/copy-media/{run_id}")
        assert resp.status_code == 200
        mock_copy.assert_called_once()
    finally:
        _RUNS.pop(run_id, None)
