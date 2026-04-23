"""Flask web UI for CAST — local server, no data leaves the machine except to OpenAI."""
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
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from cast.core import _default_anki_media_path, copy_media  # noqa: E402

load_dotenv()

# In-memory run state. Keyed by run_id (timestamp string).
# Value: {
#   "queue": Queue,
#   "output_path": Path,
#   "status": "running"|"done"|"error",
#   "platform": str,
#   "anki_media_path": str | None,
#   "cards": list[dict],   # accumulated card_done payloads for preview
#   "summary": dict | None,
# }
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
        _RUNS[run_id] = {
            "queue": q,
            "output_path": output_file_path,
            "status": "running",
            "platform": platform,
            "anki_media_path": anki_media,
            "cards": [],
            "summary": None,
        }

        def _intercept(msg: str) -> None:
            """Forward to SSE queue and capture card data for the preview page."""
            try:
                event = json.loads(msg)
            except (json.JSONDecodeError, TypeError):
                q.put(msg)
                return

            if event.get("type") == "card_done":
                _RUNS[run_id]["cards"].append({
                    "n": event["n"],
                    "front": event.get("front", ""),
                    "back": event.get("back", ""),
                    "flagged": event.get("flagged", False),
                    "cost_usd": event.get("cost_usd", 0.0),
                })
            elif event.get("type") == "done":
                _RUNS[run_id]["summary"] = {
                    "total": event.get("total", 0),
                    "skipped": event.get("skipped", 0),
                    "cost_usd": event.get("cost_usd", 0.0),
                }

            # Strip front/back from SSE payload to keep SSE messages small
            sse_event = {k: v for k, v in event.items() if k not in ("front", "back")}
            q.put(json.dumps(sse_event))

        def _worker():
            try:
                from cast.core import run_pipeline
                from cast.parsers import get_parser

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
                    progress_callback=_intercept,
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

    @app.route("/results/<run_id>")
    def results(run_id):
        run = _RUNS.get(run_id)
        if not run:
            return redirect(url_for("index"))
        return render_template(
            "results.html",
            run_id=run_id,
            cards=run["cards"],
            summary=run.get("summary") or {},
            platform=run["platform"],
        )

    @app.route("/copy-media/<run_id>", methods=["POST"])
    def copy_media_route(run_id):
        run = _RUNS.get(run_id)
        if not run:
            return jsonify({"error": "Run not found."}), 404

        anki_media_path = run.get("anki_media_path")
        if not anki_media_path:
            default = _default_anki_media_path()
            if default is None:
                return jsonify({"error": "Anki media folder could not be determined. Pass the path explicitly."}), 400
            anki_media_path = str(default)

        # Collect image paths from all stored cards (cards don't store image_paths,
        # so we re-derive them from the output directory companion folder)
        output_path = run.get("output_path")
        if not output_path or not Path(anki_media_path).exists():
            return jsonify({"error": "Anki media folder not found.", "path": anki_media_path}), 400

        # Scan for *_files/ directories adjacent to the output file
        # (images were already copied to collection.media during the run if anki_media_path
        # was set; this endpoint is for cases where it wasn't set or needs to be re-run)
        image_paths: list[str] = []
        output_dir = output_path.parent
        for files_dir in output_dir.glob("*_files"):
            if files_dir.is_dir():
                for img in files_dir.iterdir():
                    if img.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"}:
                        image_paths.append(str(img))

        copied = copy_media(image_paths, anki_media_path)
        return jsonify({"copied": len(copied), "files": copied})

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

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        import traceback as _tb

        tb_text = _tb.format_exc()
        return render_template("error.html", error=str(exc), traceback=tb_text), 500

    return app
