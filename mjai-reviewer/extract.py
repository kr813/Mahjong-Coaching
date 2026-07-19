from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup


# --- 牌ID抽出 ---
def get_tile_id(tag: Any) -> str | None:
    if not tag:
        return None
    return tag.get("href", "").replace("#pai-", "")


# --- 手牌と副露を分離せずすべて取得する関数 ---
def extract_tiles(entry: Any) -> tuple[list[str], list[str]]:
    """
    手牌・副露を分けず、tehai-state内のすべての牌を抽出する
    """
    tehai: list[str] = []

    tehai_ul = entry.find("ul", class_="tehai-state")
    if not tehai_ul:
        return tehai, []

    for use_tag in tehai_ul.find_all("use"):
        tile_id = get_tile_id(use_tag)
        if tile_id:
            tehai.append(tile_id)

    return tehai, []


def find_player_discard(entry: Any) -> str | None:
    """実HTMLでは style 付き span ではなく、Player: / Akochan: の文脈にある tile を拾う。"""
    for span in entry.find_all("span"):
        text = span.get_text(" ", strip=True)
        if not text:
            continue
        if text.startswith("Player:") or text.startswith("Akochan:"):
            use_tag = span.find("use")
            if use_tag:
                return get_tile_id(use_tag)
            for child in span.find_all("svg"):
                use_tag = child.find("use")
                if use_tag:
                    return get_tile_id(use_tag)

    player_span = entry.find("span", style=lambda s: s and "background" in s)
    if player_span and player_span.find("use"):
        return get_tile_id(player_span.find("use"))

    return None


# --- 局と巡目の取得 ---
def get_kyoku_and_turn(entry: Any) -> tuple[str, int]:
    section = entry.find_parent("section")
    kyoku = "Unknown"
    if section:
        h1 = section.find("h1", class_="kyoku-heading")
        if h1:
            kyoku = h1.find("div").get_text(strip=True) if h1.find("div") else h1.get_text(strip=True)

    summary = entry.find("summary").get_text(strip=True)
    turn_match = re.search(r"Turn\s+(\d+)", summary, re.IGNORECASE)
    turn = int(turn_match.group(1)) if turn_match else 0
    return kyoku, turn


def get_ev_from_row(row: Any) -> float:
    tds = row.find_all("td")
    if len(tds) < 2:
        return 0.0
    ev_td = tds[1]
    int_part = ev_td.find("span", class_="int")
    frac_part = ev_td.find("span", class_="frac")
    val_str = (int_part.text.strip() if int_part else "0") + (frac_part.text.strip() if frac_part else "0")
    try:
        return float(val_str)
    except ValueError:
        return 0.0


def extract_max_loss_turn(html_path: str) -> dict[str, Any] | None:
    for enc in ["utf-8", "utf-16", "cp932", "utf-8-sig"]:
        try:
            with open(html_path, "r", encoding=enc) as f:
                content = f.read()
            soup = BeautifulSoup(content, "html.parser")
            break
        except UnicodeDecodeError:
            continue
    else:
        raise Exception("どのエンコーディングでもファイルを読み込めませんでした。")

    max_loss = -1.0
    max_loss_data: dict[str, Any] | None = None

    for section in soup.find_all("section"):
        for entry in section.find_all("details", class_="entry"):
            kyoku, turn = get_kyoku_and_turn(entry)

            table = entry.find("table", class_="data")
            if not table:
                continue

            tbody = table.find("tbody")
            if not tbody:
                continue

            rows = tbody.find_all("tr")
            if not rows:
                continue

            ai_best_row = rows[0]
            ai_ev = get_ev_from_row(ai_best_row)

            player_discard = find_player_discard(entry)
            player_ev = ai_ev
            for row in rows:
                row_tile = get_tile_id(row.find("use"))
                if row_tile and player_discard and row_tile == player_discard:
                    player_ev = get_ev_from_row(row)
                    break

            loss = ai_ev - player_ev
            if loss > max_loss:
                max_loss = loss
                tehai, _ = extract_tiles(entry)

                max_loss_data = {
                    "kyoku": kyoku,
                    "turn": turn,
                    "tehai": tehai,
                    "player_discard": player_discard,
                    "player_ev": round(player_ev, 5),
                    "ai_discard": get_tile_id(ai_best_row.find("use")),
                    "ai_ev": round(ai_ev, 5),
                    "loss": round(loss, 5),
                }
    return max_loss_data


def extract_report(html_path: str) -> dict[str, Any] | None:
    max_loss_turn = extract_max_loss_turn(html_path)
    if max_loss_turn is None:
        return {"error": "No analysable report entries were found."}
    return {"max_loss_turn": max_loss_turn}
