# 麻雀AIコーチング (Mahjong-Coaching)

AI (Akochan) の麻雀牌譜解析結果から最も損失期待値（Loss）の大きかった打牌を抽出し、OCI (Oracle Cloud Infrastructure) の Generative AI Agent を通じて人間にわかりやすいアドバイス（麻雀コーチング）を提供するWebアプリケーションです。

## プロジェクト構成

- **`backend/`**: Flaskサーバーおよび各種解析処理スクリプト
  - **`app.py`**: アプリケーションのメインエントリーポイント（Flask）
  - **`interactllm.py`**: OCI Generative AI Agentとの連携モジュール
  - **`interactakochan.py`**: Akochanの解析エンジンと連携するモジュール
  - **`extract.py`**: 解析レポート（HTML/JSON）からデータをパース・抽出するモジュール
  - **`frontend.html`**: 解析の実行とアドバイスの表示を行うリッチなWeb UI（3D麻雀牌表示、マークダウン対応アドバイス）
  - **`prompt.txt`**: AIコーチ向けのシステムプロンプト設定ファイル
  - **`requirements.txt`**: 依存Pythonパッケージ定義

## 前提条件

- Python 3.10以上
- OCI (Oracle Cloud Infrastructure) のアカウントおよび Generative AI Agent のエンドポイント
- ローカル環境またはOCI環境での認証情報の設定（インスタンス・プリンシパルまたは `~/.oci/config`）

## セットアップと起動手順

### 1. 依存ライブラリのインストール
`backend` ディレクトリへ移動し、必要なパッケージをインストールします。

```bash
cd backend
pip install -r requirements.txt
```

### 2. アプリケーションの起動
Flaskサーバーを起動します。

```bash
python app.py
```
サーバーは `http://localhost:8000` で起動します。

### 3. フロントエンドの利用
ブラウザで `http://localhost:8000` にアクセスすると、Web UIが表示されます。
ここから以下の方法で麻雀の打牌解析とアドバイス生成を実行できます：
- **ファイル**: Akochanの解析レポート（JSON/HTML形式）をアップロード
- **URL**: 天鳳のログURLを入力して解析
- **JSON入力**: 解析済みのJSONデータを直接入力

## API エンドポイント

### `POST /report`
牌譜解析とLLMアドバイスを実行し、結果をJSON形式で返却します。

- **クエリパラメータ**:
  - `seat`: プレイヤーの席番号 (0: 東家, 1: 南家, 2: 西家, 3: 北家)
  - `source_type`: データソースの種類 (`file` / `url` / `json`)
  - `url`: 天鳳ログのURL (source_type=url時のみ必須)
- **リクエストボディ**:
  - `file` (Multipart/form-data, source_type=file時)
  - JSONデータ (raw body, source_type=json時)