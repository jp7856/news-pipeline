"""웹 대시보드 — 토픽 입력 → 콘텐츠 제작 파이프라인 실행 → 결과 확인."""

import sys
import threading
import logging
from dataclasses import asdict
from pathlib import Path

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator import Orchestrator
from models import ContentPackage, Level, Section

app = Flask(__name__)
app.config["SECRET_KEY"] = "news-pipeline-secret"
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
socketio = SocketIO(app, cors_allowed_origins="*")


@app.after_request
def add_no_cache(response):
    """브라우저 캐시 방지 — 항상 최신 템플릿을 전달."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

logger = logging.getLogger(__name__)

_last_result: ContentPackage | None = None
_is_running = False


@app.route("/")
def index():
    levels = [{"value": lv.value, "label": lv.value.upper()} for lv in Level]
    sections = [{"value": sc.value, "label": sc.value} for sc in Section]
    return render_template("index.html", levels=levels, sections=sections)


@app.route("/api/status")
def api_status():
    return jsonify({
        "is_running": _is_running,
        "has_result": _last_result is not None,
    })


@app.route("/api/run", methods=["POST"])
def api_run():
    global _is_running
    if _is_running:
        return jsonify({"error": "Pipeline already running."}), 409

    data = request.json
    topic = data.get("topic", "").strip()
    level_str = data.get("level", "junior")
    section_str = data.get("section", "환경")

    if not topic:
        return jsonify({"error": "Topic is required."}), 400

    try:
        level = Level(level_str)
        section = Section(section_str)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    _is_running = True
    thread = threading.Thread(target=_run_pipeline, args=(topic, level, section), daemon=True)
    thread.start()
    return jsonify({"message": "Pipeline started"})


@app.route("/api/result")
def api_result():
    if _last_result is None:
        return jsonify({"error": "No result yet."}), 404
    return jsonify(_serialize(_last_result))


def _run_pipeline(topic: str, level: Level, section: Section):
    global _last_result, _is_running
    try:
        def emit_log(msg: str):
            socketio.emit("log", {"message": msg})

        orchestrator = Orchestrator(log_callback=emit_log)
        _last_result = orchestrator.run(topic, level, section)
        socketio.emit("pipeline_done", {"result": _serialize(_last_result)})
    except Exception as e:
        socketio.emit("log", {"message": f"FATAL ERROR: {e}"})
        socketio.emit("pipeline_error", {"error": str(e)})
    finally:
        _is_running = False


def _serialize(pkg: ContentPackage) -> dict:
    return {
        "topic": pkg.topic,
        "level": pkg.level.value,
        "section": pkg.section.value,
        "article": {
            "text": pkg.article.text,
            "text_ko": pkg.article.text_ko,
            "summary_ko": pkg.article.summary_ko,
            "word_count": pkg.article.word_count,
            "vocabulary": pkg.article.vocabulary,
            "sources": pkg.article.sources,
        },
        "plagiarism": {
            "passed": pkg.plagiarism_report.passed,
            "checklist": pkg.plagiarism_report.checklist,
            "notes": pkg.plagiarism_report.notes,
        },
        "editing": [
            {"original": s.original, "suggestion": s.suggestion, "reason": s.reason}
            for s in pkg.editing_suggestions
        ],
        "crossword": [
            {
                "word": c.word,
                "korean_definition": c.korean_definition,
                "sentence_b1": c.sentence_b1,
                "sentence_b1_b2": c.sentence_b1_b2,
            }
            for c in pkg.crossword_sentences
        ],
        "workbook": [
            {
                "set_number": w.set_number,
                "vocabulary_activity": w.vocabulary_activity,
                "true_false": w.true_false,
                "comprehension_questions": w.comprehension_questions,
                "discussion_questions": w.discussion_questions,
            }
            for w in pkg.workbook_sets
        ],
    }


if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
