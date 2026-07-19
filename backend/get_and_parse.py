import urllib.request
import urllib.parse
import json
from pathlib import Path
from datetime import datetime

url = "http://localhost:8000/report?seat=0&source_type=url&url=https://tenhou.net/0/?log=2026071211gm-0009-0000-4888ed75&tw=1"
req = urllib.request.Request(url, method="POST")

print("Sending POST request to localhost:8000...")
try:
    with urllib.request.urlopen(req, timeout=300) as response:
        status = response.status
        body = response.read().decode("utf-8")
        print(f"Status: {status}")
        
        # JSONをパース
        data = json.loads(body)
        
        # llm_adviceが本当に含まれていないか確認
        if "llm_advice" in data:
            print("WARNING: llm_advice is still present in response!")
            print(f"llm_advice content: {data['llm_advice']}")
        else:
            print("SUCCESS: llm_advice has been removed from response.")
        
        # resultフォルダに保存
        result_dir = Path(__file__).resolve().parent / "result"
        result_dir.mkdir(parents=True, exist_ok=True)
        
        # レスポンス全体を保存
        json_path_raw = result_dir / "report_response.json"
        json_path_raw.write_text(body, encoding="utf-8")
        print(f"Saved raw response to {json_path_raw}")
        
        # 個別ファイルを保存
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        json_path = result_dir / f"url-{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved JSON to {json_path}")
        
except Exception as e:
    import traceback
    traceback.print_exc()
