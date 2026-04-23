"""Flask web UI for HEART — local server, no data leaves the machine except to OpenAI."""
import json
import os
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from queue import Queue

from dotenv import load_dotenv, set_key
from flask import (
    Flask,
    Response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

load_dotenv()

# In-memory run state. Keyed by run_id (timestamp string).
# Value: {"queue": Queue, "output_path": Path, "status": "running"|"done"|"error"}
_RUNS: dict[str, dict] = {}

_SENTINEL = None  # put into queue to signal SSE stream to close


def create_app(output_dir: Path | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["OUTPUT_DIR"] = Path(output_dir) if output_dir else Path("gen_anki")

    # ── Routes ────────────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        if not os.environ.get("OPENAI_API_KEY"):
            return redirect(url_for("setup"))
        return render_template("index.html")

    @app.route("/setup", methods=["GET"])
    def setup():
        return render_template("setup.html")

    @app.route("/setup", methods=["POST"])
    def setup_post():
        api_key = request.form.get("api_key", "").strip()
        if api_key:
            env_path = Path(".env")
            env_path.touch(exist_ok=True)
            set_key(str(env_path), "OPENAI_API_KEY", api_key)
            load_dotenv(override=True)
        return redirect(url_for("index"))

    @app.route("/run", methods=["POST"])
    def run():
        platform = request.form.get("platform", "uworld")
        tags = request.form.get("tags") == "on"
        validate = request.form.get("validate") == "on"
        fmt = request.form.get("format", "basic")
        anki_media = request.form.get("anki_media", "").strip() or None

        uploaded_files = request.files.getlist("files")
        if not uploaded_files or all(f.filename == "" for f in uploaded_files):
            return render_template("index.html", error="Please select at least one file.")

        # Save uploads to a temp directory
        tmp_dir = Path(tempfile.mkdtemp())
        for f in uploaded_files:
            if f.filename:
                f.save(tmp_dir / Path(f.filename).name)

        # Determine input path: NBME gets the single .txt file, others get the dir
        if platform == "nbme":
            txt_files = list(tmp_dir.glob("*.txt"))
            input_path = txt_files[0] if txt_files else tmp_dir
        else:
            input_path = tmp_dir

        run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = app.config["OUTPUT_DIR"]
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file_path = output_dir / f"{run_id}.txt"

        q: Queue = Queue()
        _RUNS[run_id] = {"queue": q, "output_path": output_file_path, "status": "running"}

        def _worker():
            try:
                from heart.core import run_pipeline
                from heart.parsers import get_parser

                parse_fn, system_prompt = get_parser(platform)
                run_pipeline(
                    parse_fn=parse_fn,
                    system_prompt=system_prompt,
                    input_path=input_path,
                    output_dir=output_dir,
                    anki_media_path=anki_media,
                    tags=tags,
                    validate=validate,
                    format=fmt,
                    progress_callback=q.put,
                    output_file_path=output_file_path,
                )
                _RUNS[run_id]["status"] = "done"
            except Exception as exc:
                _RUNS[run_id]["status"] = "error"
                q.put(json.dumps({"type": "error", "message": str(exc)}))
            finally:
                q.put(_SENTINEL)
                shutil.rmtree(tmp_dir, ignore_errors=True)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

        return redirect(url_for("progress", run_id=run_id))

    @app.route("/progress/<run_id>")
    def progress(run_id):
        if run_id not in _RUNS:
            return redirect(url_for("index"))
        return render_template("progress.html", run_id=run_id)

    @app.route("/stream/<run_id>")
    def stream(run_id):
        if run_id not in _RUNS:
            return Response("data: {}\n\n", mimetype="text/event-stream")

        def _generate():
            q = _RUNS[run_id]["queue"]
            while True:
                msg = q.get()
                if msg is _SENTINEL:
                    break
                yield f"data: {msg}\n\n"

        return Response(
            _generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.route("/download/<run_id>")
    def download(run_id):
        run = _RUNS.get(run_id)
        if not run:
            return "Run not found.", 404
        output_path = run["output_path"]
        if not output_path.exists():
            return "Output file not found.", 404
        return send_file(
            output_path.resolve(),
            as_attachment=True,
            download_name=output_path.name,
            mimetype="text/plain",
        )

    return app
