from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, Response, jsonify, request

import extract

app = Flask(__name__)

REVIEWER_BINARY = os.environ.get("MJAI_REVIEWER_BINARY", "./mjai-reviewer")


def build_command(source_type: str, source: str, seat: str, engine: str, no_open: bool) -> list[str]:
    cmd = [REVIEWER_BINARY, "-e", engine]
    if no_open:
        cmd.append("--no-open")

    if source_type == "url":
        cmd.extend(["-u", source])
    elif source_type == "log":
        cmd.extend(["-t", source])
    else:
        cmd.extend(["-i", source])

    cmd.extend(["-a", seat, "-o", "-"])
    return cmd


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


@app.route("/report", methods=["POST"])
def report() -> Response:
    seat = request.args.get("seat", "0")
    if seat not in {"0", "1", "2", "3"}:
        return jsonify(error="seat must be 0,1,2 or 3"), 400

    engine = (request.args.get("engine", "akochan") or "akochan").strip()
    no_open = True
    if request.args.get("open", "").strip().lower() in {"1", "true", "yes", "on"}:
        no_open = False
    elif request.args.get("no_open", "").strip().lower() in {"0", "false", "no", "off"}:
        no_open = False

    source_type = (request.args.get("source_type", "") or "").strip().lower()
    if not source_type:
        if request.args.get("url", "").strip():
            source_type = "url"
        elif request.args.get("log", "").strip():
            source_type = "log"
        elif request.args.get("input", "").strip():
            source_type = "file"
        elif request.is_json or "file" in request.files:
            source_type = "file"
        else:
            return jsonify(error="Provide source_type=url/log/file, or query parameter 'url'/'log'"), 400

    source_path: str | None = None
    temp_html_path: Path | None = None
    try:
        if source_type == "url":
            source = request.args.get("url", "").strip()
            if not source:
                return jsonify(error="query parameter 'url' is required"), 400
        elif source_type == "log":
            source = request.args.get("log", "").strip()
            if not source:
                return jsonify(error="query parameter 'log' is required"), 400
        else:
            input_path = request.args.get("input", "").strip()
            if input_path:
                if not os.path.exists(input_path):
                    return jsonify(error=f"input file not found: {input_path}"), 400
                source = input_path
            elif "file" in request.files:
                body = request.files["file"].read()
                if not body:
                    return jsonify(error="uploaded file is empty"), 400
                temp_source = _write_temp_file(".json", body)
                source = str(temp_source)
                source_path = str(temp_source)
            elif request.is_json:
                body = request.get_data()
                if not body:
                    return jsonify(error="request body is empty"), 400
                temp_source = _write_temp_file(".json", body)
                source = str(temp_source)
                source_path = str(temp_source)
            else:
                return jsonify(error="provide a file upload or JSON body for source_type=file"), 400

        cmd = build_command(source_type, source, seat, engine, no_open)
        process = subprocess.run(cmd, capture_output=True, text=True)
        if process.returncode != 0:
            return Response(process.stderr or f"command failed with code {process.returncode}", status=500, mimetype="text/plain")

        temp_html_path = _write_temp_file(".html", process.stdout.encode("utf-8"))
        parsed_data = extract.extract_report(str(temp_html_path))
        if parsed_data is None:
            parsed_data = {}
        return jsonify(
            source_type=source_type,
            seat=int(seat),
            parsed_report=parsed_data,
        )
    finally:
        if source_path is not None:
            _remove_file(Path(source_path))
        if temp_html_path is not None:
            _remove_file(temp_html_path)


@app.route("/healthz", methods=["GET"])
def healthz() -> Response:
    return Response("OK", mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
