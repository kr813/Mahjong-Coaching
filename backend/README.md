# 連絡事項
- index.htmlの配置パスは Mahjong-Coaching/frontend/index.htmlでお願いします
- /reportにPOSTする形でファイルのを受け渡してください
- 

# backend

A small Flask backend that runs `mjai-reviewer` in Docker and returns HTML output.

## Requirements

- Python 3.10+
- Docker installed and usable by this user
- `mjai-reviewer:latest` or another OCI image available locally or pullable

## Install

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
cd backend
python app.py
```

The service listens on `http://0.0.0.0:8000`.

## Usage

### JSON body

```bash
curl -X POST http://localhost:8000/report?seat=0 \
  -H "Content-Type: application/json" \
  -d @../akochan-docker/mjai-reviewer/test.json > report.html
```

### File upload

```bash
curl -X POST http://localhost:8000/report?seat=0 \
  -F "file=@../akochan-docker/mjai-reviewer/test.json" > report.html
```

## Environment

- `MJAI_REVIEWER_IMAGE`: optional image name, default `mjai-reviewer:latest`

## callreport.py

`callreport.py` は、akochanサーバへ必要な情報を渡し、akochan解析結果(html)を返す関数です

### 引数

- `--file <path>`: ローカルの JSON ファイルを multipart 形式でアップロードします
- `--json <path>`: sourceディレクトリ配下のJSON ファイルの内容をリクエストボディとして送信します
- `--url <url>`: 天鳳のログ URL を送信します
- `--seat <0-3>`: 自家の番号。デフォルトは `0`
- `--endpoint <url>`: 呼び出す API の URL。デフォルトは `http://localhost:8000/report`

### 処理内容

このスクリプトは `curl` コマンドを組み立て、POST リクエストを送信し、返ってきた HTML を指定したファイルに保存します。

### 例
python callreport.py --file test.json --seat 0
python callreport.py --json test.json --seat 0
python callreport.py --url "https://tenhou.net/0/?log=2026071211gm-0009-0000-4888ed75&tw=1" --seat 0

出力は `backend/result` 配下に `file-YYYYMMDD-HHMMSS.html` などの自動生成名で保存されます。
