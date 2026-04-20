"""Google Sheets を DB として扱うストレージ層。

各タブを「テーブル」として扱い、gspread で読み書きする。
auto_increment の id は既存行の最大値+1 で採番。

設計方針:
- 読み込みはタブごとに `get_all_records()` で一括取得(Python側でJOIN)
- 書き込みはバッチで `append_rows()` を使い、レート制限を意識
- スキーマ(ヘッダ)は SHEETS_SCHEMA で定義し、init時に書き込み
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Optional

import gspread
from google.oauth2.service_account import Credentials

from .config import GOOGLE_CREDENTIALS_PATH, SPREADSHEET_ID


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# タブ構成 — 列名と順序を固定する
SHEETS_SCHEMA: dict[str, list[str]] = {
    "products": [
        "id", "name", "category", "jan", "asin", "sku",
        "url_amazon", "url_rakuten", "url_mercari", "url_yahoo",
        "memo", "created_at", "updated_at",
    ],
    "purchases": [
        "id", "product_id", "purchase_date", "source", "store_name",
        "unit_price", "quantity", "shipping_in", "point_back",
        "memo", "created_at",
    ],
    "sales": [
        "id", "purchase_id", "sale_date", "channel",
        "sale_price", "quantity", "platform_fee", "fba_fee",
        "shipping_out", "other_cost", "memo", "created_at",
    ],
    "sourced_items": [
        "id", "source", "source_item_id", "product_id", "asin", "jan",
        "title", "price", "shop_name", "url", "image_url",
        "postage_flag", "point_rate", "review_avg", "review_count",
        "query", "memo", "fetched_at",
    ],
    "price_history": [
        "id", "product_id", "source", "price", "sales_rank", "fetched_at",
    ],
}


class SheetsError(Exception):
    pass


@lru_cache(maxsize=1)
def _client() -> gspread.Client:
    if not SPREADSHEET_ID:
        raise SheetsError("SPREADSHEET_ID が未設定です。.env を確認してください。")
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


@lru_cache(maxsize=1)
def _spreadsheet():
    return _client().open_by_key(SPREADSHEET_ID)


@lru_cache(maxsize=32)
def _ws(name: str) -> gspread.Worksheet:
    sh = _spreadsheet()
    try:
        return sh.worksheet(name)
    except gspread.WorksheetNotFound:
        raise SheetsError(f"タブ '{name}' が存在しません。先に `python sedori.py sheets init` を実行してください。")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- 初期化 ----------
def init_sheets() -> list[str]:
    """定義されたタブを作成しヘッダ行を書き込む。既存タブは触らない。"""
    sh = _spreadsheet()
    existing = {w.title: w for w in sh.worksheets()}
    created = []
    for name, headers in SHEETS_SCHEMA.items():
        if name in existing:
            # ヘッダ行をチェックして不足があれば整える
            ws = existing[name]
            current = ws.row_values(1)
            if current != headers:
                ws.update(range_name="A1", values=[headers])
            continue
        ws = sh.add_worksheet(title=name, rows=200, cols=max(10, len(headers)))
        ws.update(range_name="A1", values=[headers])
        ws.freeze(rows=1)
        created.append(name)
    # デフォルトの "シート1" があれば末尾へ移動(削除は破壊的なので避ける)
    if "シート1" in existing and len(existing) == 1:
        try:
            sh.del_worksheet(existing["シート1"])
        except Exception:
            pass
    return created


def init_dashboard() -> None:
    """dashboard タブを作成しQUERY関数でサマリを自動計算。"""
    sh = _spreadsheet()
    existing = {w.title for w in sh.worksheets()}
    if "dashboard" in existing:
        ws = sh.worksheet("dashboard")
    else:
        ws = sh.add_worksheet(title="dashboard", rows=50, cols=10)
        ws.freeze(rows=1)

    # 集計用のQUERYフォーミュラ(QUERY関数は英語ロケールで動作)
    content = [
        ["=== 月次サマリ ==="],
        ["month", "sales", "profit", "件数"],
        ['=IFERROR(QUERY({ARRAYFORMULA(LEFT(sales!C2:C,7)), sales!E2:E*sales!F2:F, '
         'sales!E2:E*sales!F2:F - sales!G2:G - sales!H2:H - sales!I2:I - sales!J2:J, sales!A2:A}, '
         '"select Col1, sum(Col2), sum(Col3), count(Col4) where Col1 is not null group by Col1 label Col1 \'\', sum(Col2) \'\', sum(Col3) \'\', count(Col4) \'\'", 0), "")'],
        [""],
        ["=== 販路別 ==="],
        ["channel", "sales", "件数"],
        ['=IFERROR(QUERY({sales!D2:D, sales!E2:E*sales!F2:F, sales!A2:A}, '
         '"select Col1, sum(Col2), count(Col3) where Col1 is not null group by Col1 label Col1 \'\', sum(Col2) \'\', count(Col3) \'\'", 0), "")'],
    ]
    ws.update(range_name="A1", values=content)


# ---------- 行操作 ----------
def all_records(name: str) -> list[dict]:
    ws = _ws(name)
    return ws.get_all_records()


def next_id(name: str) -> int:
    records = all_records(name)
    if not records:
        return 1
    ids = [int(r["id"]) for r in records if r.get("id") not in (None, "")]
    return (max(ids) + 1) if ids else 1


def append(name: str, row: dict) -> int:
    """row を dict で受け取り、スキーマ順に並べて追記。新規IDを返す。"""
    schema = SHEETS_SCHEMA[name]
    if "id" in schema and not row.get("id"):
        row["id"] = next_id(name)
    for col in ("created_at", "fetched_at"):
        if col in schema and not row.get(col):
            row[col] = _now()
    if "updated_at" in schema and not row.get("updated_at"):
        row["updated_at"] = _now()
    values = [_cell(row.get(col, "")) for col in schema]
    _ws(name).append_row(values, value_input_option="USER_ENTERED")
    return int(row["id"]) if "id" in schema else 0


def append_many(name: str, rows: list[dict]) -> list[int]:
    if not rows:
        return []
    schema = SHEETS_SCHEMA[name]
    ids: list[int] = []
    next_i = next_id(name) if "id" in schema else 0
    batch = []
    for row in rows:
        if "id" in schema and not row.get("id"):
            row["id"] = next_i
            next_i += 1
        for col in ("created_at", "fetched_at"):
            if col in schema and not row.get(col):
                row[col] = _now()
        batch.append([_cell(row.get(col, "")) for col in schema])
        if "id" in schema:
            ids.append(int(row["id"]))
    _ws(name).append_rows(batch, value_input_option="USER_ENTERED")
    return ids


def find_one(name: str, **where) -> Optional[dict]:
    for r in all_records(name):
        if all(str(r.get(k)) == str(v) for k, v in where.items()):
            return r
    return None


def find_all(name: str, **where) -> list[dict]:
    out = []
    for r in all_records(name):
        if all(str(r.get(k)) == str(v) for k, v in where.items()):
            out.append(r)
    return out


def find_by_id(name: str, row_id: int) -> Optional[dict]:
    return find_one(name, id=row_id)


def update_by_id(name: str, row_id: int, **updates) -> bool:
    """id で行を検索して指定列を更新。見つからなければ False。"""
    ws = _ws(name)
    schema = SHEETS_SCHEMA[name]
    records = ws.get_all_records()
    target_row = None
    for i, r in enumerate(records, start=2):  # 1行目はヘッダ
        if str(r.get("id")) == str(row_id):
            target_row = i
            break
    if target_row is None:
        return False
    if "updated_at" in schema and "updated_at" not in updates:
        updates["updated_at"] = _now()
    batch = []
    for col, val in updates.items():
        if col not in schema:
            continue
        col_idx = schema.index(col) + 1  # A=1
        batch.append({
            "range": gspread.utils.rowcol_to_a1(target_row, col_idx),
            "values": [[_cell(val)]],
        })
    if batch:
        ws.batch_update(batch, value_input_option="USER_ENTERED")
    return True


def delete_by_id(name: str, row_id: int) -> bool:
    ws = _ws(name)
    records = ws.get_all_records()
    for i, r in enumerate(records, start=2):
        if str(r.get("id")) == str(row_id):
            ws.delete_rows(i)
            return True
    return False


def _cell(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, bool):
        return 1 if v else 0
    return v
