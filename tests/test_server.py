"""Tests for the CAST Flask web UI (cast/server/app.py)."""
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cast.server.app import _RUNS, create_app


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
    with patch("cast.server.app.set_key") as mock_set, \
         patch("cast.server.app.load_dotenv"):
        resp = client.post("/setup", data={"api_key": "sk-abc123"})
    mock_set.assert_called_once_with(str(Path(".env")), "OPENAI_API_KEY", "sk-abc123")
    assert resp.status_code == 302
    assert "/" in resp.headers["Location"]


def test_setup_post_empty_key_still_redirects(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("cast.server.app.set_key") as mock_set, \
         patch("cast.server.app.load_dotenv"):
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

    with patch("cast.server.app.threading.Thread") as mock_thread_cls, \
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


# ── Global error handler ──────────────────────────────────────────────────────


def test_global_error_handler_returns_500(client):
    """An unhandled exception in any route renders the error.html page with HTTP 500."""
    from cast.server.app import create_app

    app = create_app()
    app.config["TESTING"] = True

    @app.route("/explode")
    def explode():
        raise RuntimeError("kaboom")

    with app.test_client() as c:
        resp = c.get("/explode")
    assert resp.status_code == 500
    assert b"kaboom" in resp.data
    assert b"Something went wrong" in resp.data


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
        with patch("cast.server.app.copy_media", return_value=[]) as mock_copy:
            resp = client.post(f"/copy-media/{run_id}")
        assert resp.status_code == 200
        mock_copy.assert_called_once()
    finally:
        _RUNS.pop(run_id, None)


# ── /run: NBME input-path selection (lines 88-89) ────────────────────────────


def test_run_nbme_uses_txt_file_as_input(client):
    """NBME platform sets input_path to the uploaded .txt file, not the directory."""
    txt_content = b"Question 1.\nA. Option A\nB. Option B\n\nAnswer: A\n"
    dummy_file = (io.BytesIO(txt_content), "nbme_form.txt")
    captured: dict = {}

    def fake_pipeline(*args, input_path=None, **kwargs):
        captured["input_path"] = input_path

    with patch("cast.server.app.threading.Thread") as mock_thread_cls, \
         patch("cast.core.run_pipeline", side_effect=fake_pipeline), \
         patch("cast.parsers.get_parser", return_value=(MagicMock(), "prompt")), \
         patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):

        mock_thread_cls.return_value = MagicMock()
        resp = client.post(
            "/run",
            data={"platform": "nbme", "files": dummy_file},
            content_type="multipart/form-data",
        )
        run_id = resp.headers["Location"].split("/progress/")[-1]
        mock_thread_cls.call_args.kwargs["target"]()

    try:
        assert captured["input_path"].name == "nbme_form.txt"
    finally:
        _RUNS.pop(run_id, None)


# ── _worker and _intercept (lines 111-160) ────────────────────────────────────


def test_worker_runs_pipeline_and_intercepts_all_message_types(client):
    """Worker happy path: _intercept handles non-JSON, card_done, and done events."""
    dummy_file = (io.BytesIO(b"<html></html>"), "q.html")

    card_done_msg = json.dumps({
        "type": "card_done", "n": 1,
        "front": "What is X?", "back": "X is Y.",
        "flagged": False, "cost_usd": 0.001,
    })
    done_msg = json.dumps({"type": "done", "total": 1, "skipped": 0, "cost_usd": 0.001})

    def fake_pipeline(*args, progress_callback=None, **kwargs):
        if progress_callback:
            progress_callback("not json at all")
            progress_callback(card_done_msg)
            progress_callback(done_msg)

    with patch("cast.server.app.threading.Thread") as mock_thread_cls, \
         patch("cast.core.run_pipeline", side_effect=fake_pipeline), \
         patch("cast.parsers.get_parser", return_value=(MagicMock(), "prompt")), \
         patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):

        mock_thread_cls.return_value = MagicMock()
        resp = client.post(
            "/run",
            data={"platform": "uworld", "files": dummy_file},
            content_type="multipart/form-data",
        )
        run_id = resp.headers["Location"].split("/progress/")[-1]
        mock_thread_cls.call_args.kwargs["target"]()

    try:
        assert _RUNS[run_id]["status"] == "done"
        assert len(_RUNS[run_id]["cards"]) == 1
        assert _RUNS[run_id]["cards"][0]["front"] == "What is X?"
        assert _RUNS[run_id]["summary"]["total"] == 1
    finally:
        _RUNS.pop(run_id, None)


def test_worker_error_propagates_to_queue(client):
    """Worker exception path: status set to 'error' and error message queued."""
    dummy_file = (io.BytesIO(b"<html></html>"), "q.html")

    with patch("cast.server.app.threading.Thread") as mock_thread_cls, \
         patch("cast.core.run_pipeline", side_effect=ValueError("pipeline exploded")), \
         patch("cast.parsers.get_parser", return_value=(MagicMock(), "prompt")), \
         patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):

        mock_thread_cls.return_value = MagicMock()
        resp = client.post(
            "/run",
            data={"platform": "uworld", "files": dummy_file},
            content_type="multipart/form-data",
        )
        run_id = resp.headers["Location"].split("/progress/")[-1]
        mock_thread_cls.call_args.kwargs["target"]()

    try:
        assert _RUNS[run_id]["status"] == "error"
        error_msg = json.loads(_RUNS[run_id]["queue"].get_nowait())
        assert error_msg["type"] == "error"
        assert "pipeline exploded" in error_msg["message"]
    finally:
        _RUNS.pop(run_id, None)


# ── /stream SSE endpoint (lines 175-186) ─────────────────────────────────────


def test_stream_unknown_run_returns_empty_sse(client):
    resp = client.get("/stream/nonexistent-run")
    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"
    assert b"data: {}" in resp.data


def test_stream_yields_queue_messages(client, tmp_path):
    from queue import Queue
    run_id = "2026-06-01_20-00-00"
    q = Queue()
    q.put('{"type": "progress", "n": 1}')
    q.put(None)  # sentinel
    _RUNS[run_id] = {
        "queue": q,
        "output_path": tmp_path / "out.txt",
        "status": "running",
        "platform": "uworld",
        "anki_media_path": None,
        "cards": [],
        "summary": None,
    }
    try:
        resp = client.get(f"/stream/{run_id}")
        assert resp.status_code == 200
        assert resp.mimetype == "text/event-stream"
        assert b'data: {"type": "progress"' in resp.data
    finally:
        _RUNS.pop(run_id, None)


# ── /copy-media additional branches (lines 213-216, 222, 229-233) ─────────────


def test_copy_media_returns_400_when_default_path_unavailable(client, tmp_path):
    run_id = "2026-06-01_21-00-00"
    _make_run(run_id, tmp_path / "out.txt")
    try:
        with patch("cast.server.app._default_anki_media_path", return_value=None):
            resp = client.post(f"/copy-media/{run_id}")
        assert resp.status_code == 400
        assert "could not be determined" in resp.get_json()["error"]
    finally:
        _RUNS.pop(run_id, None)


def test_copy_media_uses_default_path_and_scans_images(client, tmp_path):
    anki_dir = tmp_path / "anki_media"
    anki_dir.mkdir()
    output_file = tmp_path / "gen_anki" / "run.txt"
    output_file.parent.mkdir(parents=True)
    output_file.write_text("", encoding="utf-8")

    files_dir = output_file.parent / "question_1_files"
    files_dir.mkdir()
    (files_dir / "figure.png").write_bytes(b"")
    (files_dir / "document.pdf").write_bytes(b"")

    run_id = "2026-06-01_22-00-00"
    _make_run(run_id, output_file)
    try:
        with patch("cast.server.app._default_anki_media_path", return_value=anki_dir), \
             patch("cast.server.app.copy_media", return_value=[]) as mock_copy:
            resp = client.post(f"/copy-media/{run_id}")
        assert resp.status_code == 200
        passed_images = mock_copy.call_args[0][0]
        assert any("figure.png" in p for p in passed_images)
        assert not any("document.pdf" in p for p in passed_images)
    finally:
        _RUNS.pop(run_id, None)


def test_copy_media_returns_400_when_media_folder_missing(client, tmp_path):
    from queue import Queue
    run_id = "2026-06-01_23-00-00"
    _RUNS[run_id] = {
        "queue": Queue(),
        "output_path": tmp_path / "out.txt",
        "status": "done",
        "platform": "uworld",
        "anki_media_path": str(tmp_path / "nonexistent_anki"),
        "cards": [],
        "summary": None,
    }
    try:
        resp = client.post(f"/copy-media/{run_id}")
        assert resp.status_code == 400
        assert "not found" in resp.get_json()["error"]
    finally:
        _RUNS.pop(run_id, None)
