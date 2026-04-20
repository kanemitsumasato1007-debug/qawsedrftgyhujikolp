import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "db" / "sedori.db"
SCHEMA_PATH = ROOT_DIR / "schema.sql"

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

CATEGORIES = ("ホビー", "ゲーム", "美容", "アパレル", "その他")
PURCHASE_SOURCES = ("Amazon", "楽天", "メルカリ", "ヤフオク", "ラクマ", "実店舗", "その他")
SALE_CHANNELS = ("Amazon", "Amazon FBA", "メルカリ", "ヤフオク", "ラクマ", "その他")

RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID", "")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "")
YAHOO_APP_ID = os.environ.get("YAHOO_APP_ID", "")
YAHOO_SECRET = os.environ.get("YAHOO_SECRET", "")
KEEPA_API_KEY = os.environ.get("KEEPA_API_KEY", "")

GOOGLE_CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")
