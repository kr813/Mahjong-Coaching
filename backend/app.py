from __future__ import annotations

import os

from flask import Flask, Response, jsonify, request, render_template, abort

import utils

app = Flask(__name__)


@app.route("/analyze", methods=["GET", "POST"])
def analyze() -> str | Response | tuple[str, int]:
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

    url = None
    file_content = None
    json_body = None

    if source_type == "url":
        url = (request.args.get("url") or "").strip()
        if not url:
            return jsonify(error="query parameter 'url' is required for source_type=url"), 400
    elif source_type == "file":
        uploaded_file = request.files.get("file")
        if uploaded_file is None:
            return jsonify(error="file upload is required for source_type=file"), 400
        if uploaded_file.filename == "":
            return jsonify(error="uploaded file is missing or empty"), 400
        file_content = uploaded_file.read()
    elif source_type == "json":
        if not request.is_json:
            return jsonify(error="JSON body is required for source_type=json"), 400
        json_body = request.get_data()
        if not json_body:
            return jsonify(error="JSON body is empty"), 400

    try:
        data = utils.run_analysis(
            source_type=source_type,
            seat=int(seat),
            url=url,
            file_content=file_content,
            json_body=json_body
        )
        return render_template("result.html", **data)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        error_msg = str(e)
        is_docker_error = any(
            x in error_msg.lower() 
            for x in ["docker", "npipe://", "docker.sock", "daemon", "cannot connect"]
        )
        if is_docker_error:
            error_msg = (
                "解析エンジン（Docker）に接続できませんでした。"
                "Docker デーモンが起動していること、または外部接続先（環境変数 'MJAI_REVIEWER_ENDPOINT'）"
                "が正しく設定されていることを確認してください。"
            )
        return render_template(
            "error.html",
            error_code="500",
            error_title="解析エンジンエラー",
            error_message=error_msg
        ), 500

@app.route("/", methods=["GET"])
def index() -> str:
    return render_template("index.html")


@app.route("/error", methods=["GET", "POST"])
def error() -> Response | tuple[str, int]:
    abort(500)


@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        "error.html",
        error_code="404",
        error_title="ページが見つかりません",
        error_message="お探しのページは移動または削除されたか、URLが間違っている可能性があります。"
    ), 404


@app.errorhandler(400)
def bad_request(e):
    return render_template(
        "error.html",
        error_code="400",
        error_title="不正なリクエストです",
        error_message="送信されたデータに誤りがあるか、処理できない形式のリクエストです。"
    ), 400


@app.errorhandler(500)
def internal_server_error(e):
    return render_template(
        "error.html",
        error_code="500",
        error_title="サーバーエラーが発生しました",
        error_message="バックエンド側で問題が発生しました。しばらく時間を置いてから再度お試しください。"
    ), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
