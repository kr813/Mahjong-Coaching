from __future__ import annotations
import tempfile
import json
import re
from pathlib import Path
from typing import Any

import extract
import interactakochan
import interactllm

def write_temp_file(suffix: str, content: bytes) -> Path:
    temp_file = Path(tempfile.NamedTemporaryFile(suffix=suffix, delete=False).name)
    temp_file.write_bytes(content)
    return temp_file


def remove_file(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink()
    except OSError:
        pass


def convert_tile_detail(tile_str: str | None) -> dict[str, Any]:
    if not tile_str:
        return {"emoji": "", "is_red": False}
    
    t = tile_str.lower().strip()
    is_red = False
    
    # 赤ドラ判定 (末尾が 'r')
    if t.endswith("r"):
        is_red = True
        t = t[:-1]
    
    # 字牌マップ
    zi_map = {
        "ton": "🀀", "1z": "🀀",
        "nan": "🀁", "2z": "🀁",
        "sha": "🀂", "3z": "🀂",
        "pe": "🀃", "4z": "🀃",
        "haku": "🀆", "5z": "🀆",
        "hatsu": "🀅", "6z": "🀅",
        "chun": "🀄", "7z": "🀄",
    }
    
    if t in zi_map:
        return {"emoji": zi_map[t], "is_red": is_red}
        
    # 数牌 (1m, 2p, 3s など) の判定
    match = re.match(r"^(\d)(m|p|s)$", t)
    if not match:
        match = re.match(r"^(m|p|s)(\d)$", t)
        if match:
            suit, num_str = match.groups()
        else:
            return {"emoji": tile_str, "is_red": is_red}
    else:
        num_str, suit = match.groups()
        
    num = int(num_str)
    
    # Unicodeのコードポイント計算
    if suit == "m":
        code_point = 0x1F007 + (num - 1)
    elif suit == "s":
        code_point = 0x1F010 + (num - 1)
    elif suit == "p":
        code_point = 0x1F019 + (num - 1)
    else:
        return {"emoji": tile_str, "is_red": is_red}
        
    return {"emoji": chr(code_point), "is_red": is_red}


def run_analysis(
    source_type: str,
    seat: int,
    url: str | None = None,
    file_content: bytes | None = None,
    json_body: bytes | None = None
) -> dict[str, Any]:
    html_path = None
    temp_html_path = None
    try:
        if source_type == "url":
            if not url:
                raise ValueError("query parameter 'url' is required for source_type=url")
            report_html = interactakochan.call_report(source_type="url", url=url, seat=seat)
        elif source_type == "file":
            if not file_content:
                raise ValueError("file upload is required for source_type=file")
            html_path = write_temp_file(".json", file_content)
            report_html = interactakochan.call_report(source_type="file", file_path=str(html_path), seat=seat)
        elif source_type == "json":
            if not json_body:
                raise ValueError("JSON body is required for source_type=json")
            html_path = write_temp_file(".json", json_body)
            report_html = interactakochan.call_report(source_type="json", json_path=str(html_path), seat=seat)
        else:
            raise ValueError("source_type must be one of json, file, url")

        temp_html_path = write_temp_file(".html", report_html.encode("utf-8"))
        parsed_data = extract.extract_report(str(temp_html_path))
        if parsed_data is None:
            parsed_data = {}

        # OCIのLLMと連携し、アドバイスを取得
        advice = interactllm._generate_advice(parsed_data)
        
        max_loss_turn = parsed_data.get("max_loss_turn")
        if not max_loss_turn:
            raise ValueError("No analysable report entries were found.")

        # フラットな辞書データを作成
        result_data = {
            "kyoku": max_loss_turn.get("kyoku", "Unknown"),
            "turn": max_loss_turn.get("turn", 0),
            "tehai": max_loss_turn.get("tehai", []),
            "player_discard": max_loss_turn.get("player_discard", ""),
            "ai_discard": max_loss_turn.get("ai_discard", ""),
            "loss": max_loss_turn.get("loss", 0.0),
            "commentary": advice
        }

        # 一時的に data.json に保存
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=4)

        # data.json を読み込む
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # 赤ドラ対応 of conversion
        data["tehai_data"] = [convert_tile_detail(t) for t in data["tehai"]]
        
        player_res = convert_tile_detail(data["player_discard"])
        data["player_discard"] = player_res["emoji"]
        data["player_is_red"] = player_res["is_red"]

        ai_res = convert_tile_detail(data["ai_discard"])
        data["ai_discard"] = ai_res["emoji"]
        data["ai_is_red"] = ai_res["is_red"]

        # 不要になった元キーを削除（混同防止）
        del data["tehai"]

        return data

    finally:
        remove_file(html_path)
        remove_file(temp_html_path)
