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


def test_progress_page_returns_200_for_known_run(client):
    from queue import Queue
    run_id = "2026-01-01_00-00-00"
    _RUNS[run_id] = {"queue": Queue(), "output_path": Path("/tmp/out.txt"), "status": "running"}
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


def test_download_returns_file(client, tmp_path):
    output_file = tmp_path / "gen_anki" / "2026-01-01_00-00-00.txt"
    output_file.parent.mkdir(parents=True)
    output_file.write_text("front\tback\n", encoding="utf-8")

    from queue import Queue
    run_id = "2026-01-01_00-00-00"
    _RUNS[run_id] = {"queue": Queue(), "output_path": output_file, "status": "done"}
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
    from queue import Queue
    run_id = "2026-01-01_12-00-00"
    _RUNS[run_id] = {
        "queue": Queue(),
        "output_path": tmp_path / "nonexistent.txt",
        "status": "done",
    }
    try:
        resp = client.get(f"/download/{run_id}")
        assert resp.status_code == 404
    finally:
        _RUNS.pop(run_id, None)
