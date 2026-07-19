from __future__ import annotations

import os
import tempfile
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file

import extract
import interactakochan
import interactllm

app = Flask(__name__)


def _write_temp_file(suffix: str, content: bytes) -> Path:
    temp_file = Path(tempfile.NamedTemporaryFile(suffix=suffix, delete=False).name)
    temp_file.write_bytes(content)
    return temp_file


def _remove_file(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink()
    except OSError:
        pass


@app.route("/report", methods=["GET", "POST"])
def report() -> Response | tuple[str, int]:
    seat = (request.args.get("seat") or "0").strip()
    if seat not in {"0", "1", "2", "3"}:
        return jsonify(error="seat must be 0, 1, 2, or 3"), 400

    source_type = (request.args.get("source_type") or "").strip().lower()
    if not source_type:
        if request.args.get("url", "").strip():
            source_type = "url"
        elif request.is_json:
            source_type = "json"
        elif "file" in request.files:
            source_type = "file"
        else:
            return jsonify(error="source_type is required when url/file/json is not provided"), 400

    html_path = None
    report_html = ""
    try:
        if source_type == "url":
            url = (request.args.get("url") or "").strip()
            if not url:
                return jsonify(error="query parameter 'url' is required for source_type=url"), 400
            report_html = interactakochan.call_report(source_type="url", url=url, seat=int(seat))
        elif source_type == "file":
            uploaded_file = request.files.get("file")
            if uploaded_file is None:
                return jsonify(error="file upload is required for source_type=file"), 400
            if uploaded_file.filename == "":
                return jsonify(error="uploaded file is missing or empty"), 400
            html_path = _write_temp_file(".json", uploaded_file.read())
            report_html = interactakochan.call_report(source_type="file", file_path=str(html_path), seat=int(seat))
        elif source_type == "json":
            if not request.is_json:
                return jsonify(error="JSON body is required for source_type=json"), 400
            body = request.get_data()
            if not body:
                return jsonify(error="JSON body is empty"), 400
            html_path = _write_temp_file(".json", body)
            report_html = interactakochan.call_report(source_type="json", json_path=str(html_path), seat=int(seat))
        else:
            return jsonify(error="source_type must be one of json, file, url"), 400

        temp_html_path = _write_temp_file(".html", report_html.encode("utf-8"))
        parsed_data = extract.extract_report(str(temp_html_path))
        if parsed_data is None:
            parsed_data = {}

        # OCIのLLMと連携し、アドバイスをJSONに追加して返す処理（現在は不要のためコメントアウト）
        # advice = interactllm._generate_advice(parsed_data)
        # if isinstance(parsed_data, dict):
        #     parsed_data["llm_advice"] = advice
        # return jsonify(parsed_data)

        return jsonify(parsed_data)

    finally:
        _remove_file(html_path)
        if 'temp_html_path' in locals():
            _remove_file(temp_html_path)


@app.route("/", methods=["GET"])
def index() -> Response:
    return send_file(os.path.join(os.path.dirname(__file__), "frontend.html"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
