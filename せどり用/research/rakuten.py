"""楽天市場商品検索API クライアント。

API docs: https://webservice.rakuten.co.jp/documentation/ichiba-item-search
- レート制限: 公式推奨 1req/sec
- 最大ヒット数/ページ: 30、最大ページ: 100
"""
import time
from dataclasses import dataclass, field
from typing import Optional
import requests

from shared.config import RAKUTEN_APP_ID, RAKUTEN_AFFILIATE_ID, RAKUTEN_ACCESS_KEY

# 新エンドポイント(2026年2月以降、旧 app.rakuten.co.jp は2026年5月13日で廃止)
API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"
_REQUEST_INTERVAL_SEC = 1.0
_last_request_at = 0.0

# 運要素・ギャンブル性のある商品は除外(仕入れとして不適切)
RANDOM_ITEM_KEYWORDS = (
    "福袋", "ガチャ", "オリパ", "くじ", "クジ", "ランダム",
    "ブラインド", "サプライズ", "開運", "詰め合わせ", "アソート",
    "おまかせ", "お楽しみ", "福箱", "ミステリー", "シークレット",
)


@dataclass
class RakutenItem:
    item_code: str
    title: str
    price: int
    shop_name: str
    url: str
    image_url: str
    postage_flag: int               # 0=送料込み, 1=送料別
    point_rate: float
    review_avg: float
    review_count: int
    availability: int
    raw: dict = field(repr=False, default_factory=dict)


class RakutenAPIError(Exception):
    pass


def _throttle():
    global _last_request_at
    now = time.time()
    wait = _REQUEST_INTERVAL_SEC - (now - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.time()


def _is_random_item(title: str) -> bool:
    return any(w in title for w in RANDOM_ITEM_KEYWORDS)


def search(
    keyword: str,
    *,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    genre_id: Optional[str] = None,
    sort: str = "-reviewCount",   # -reviewCount, +itemPrice, -itemPrice, +updateTimestamp
    hits: int = 30,
    page: int = 1,
    availability: int = 1,
    max_pages: int = 1,
    exclude_random: bool = True,
) -> list[RakutenItem]:
    """楽天市場を検索して RakutenItem のリストを返す。

    max_pages > 1 の場合は連続ページを取得(レート制限に注意)。
    exclude_random=True(既定) で福袋・ガチャ・オリパ・くじ等の運要素商品を除外。
    """
    if not RAKUTEN_APP_ID:
        raise RakutenAPIError(
            "RAKUTEN_APP_ID が未設定です。.env に登録してください。\n"
            "取得: https://webservice.rakuten.co.jp/ でアプリ登録(無料)"
        )
    if not RAKUTEN_ACCESS_KEY:
        raise RakutenAPIError(
            "RAKUTEN_ACCESS_KEY が未設定です。.env に登録してください。\n"
            "アプリ管理画面の「アクセスキー」欄からコピー"
        )

    results: list[RakutenItem] = []
    for p in range(page, page + max_pages):
        _throttle()
        params = {
            "applicationId": RAKUTEN_APP_ID,
            "accessKey": RAKUTEN_ACCESS_KEY,
            "format": "json",
            "keyword": keyword,
            "sort": sort,
            "hits": hits,
            "page": p,
            "availability": availability,
            "formatVersion": 2,
        }
        if RAKUTEN_AFFILIATE_ID:
            params["affiliateId"] = RAKUTEN_AFFILIATE_ID
        if min_price is not None:
            params["minPrice"] = min_price
        if max_price is not None:
            params["maxPrice"] = max_price
        if genre_id:
            params["genreId"] = genre_id

        resp = requests.get(API_URL, params=params, timeout=15)
        if resp.status_code != 200:
            raise RakutenAPIError(f"API error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        items = data.get("Items", [])
        if not items:
            break

        for it in items:
            title = it.get("itemName", "")
            if exclude_random and _is_random_item(title):
                continue
            # formatVersion=2 ではフラットな dict
            results.append(RakutenItem(
                item_code=it.get("itemCode", ""),
                title=title,
                price=int(it.get("itemPrice", 0)),
                shop_name=it.get("shopName", ""),
                url=it.get("itemUrl", ""),
                image_url=(it.get("mediumImageUrls") or [""])[0] if it.get("mediumImageUrls") else "",
                postage_flag=int(it.get("postageFlag", 0)),
                point_rate=float(it.get("pointRate", 1)),
                review_avg=float(it.get("reviewAverage", 0) or 0),
                review_count=int(it.get("reviewCount", 0) or 0),
                availability=int(it.get("availability", 0)),
                raw=it,
            ))

        if len(items) < hits:
            break  # 最終ページ
    return results
