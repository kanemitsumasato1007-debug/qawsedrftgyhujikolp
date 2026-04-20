"""Yahoo!ショッピング商品検索API (V3) クライアント。

docs: https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch
- 認証: appid クエリパラメータ(Client ID)
- レート制限: 特に明記なし(常識的な間隔で。1req/sec)
- 最大ヒット数/ページ: 50、最大offset: 100
- Rakutenと違い **janCode** を返してくれる(自動マッチング可能)
"""
import time
from dataclasses import dataclass, field
from typing import Optional
import requests

from shared.config import YAHOO_APP_ID
from .rakuten import RANDOM_ITEM_KEYWORDS, _is_random_item

API_URL = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
_REQUEST_INTERVAL_SEC = 1.0
_last_request_at = 0.0


@dataclass
class YahooItem:
    item_code: str
    jan: Optional[str]
    title: str
    price: int
    premium_price: Optional[int]     # Yahoo!プレミアム会員価格
    shop_name: str
    url: str
    image_url: str
    shipping_free: bool              # True なら送料込み
    point_amount: int                # ポイント還元額(円相当)
    review_avg: float
    review_count: int
    raw: dict = field(repr=False, default_factory=dict)


class YahooAPIError(Exception):
    pass


def _throttle():
    global _last_request_at
    now = time.time()
    wait = _REQUEST_INTERVAL_SEC - (now - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.time()


def search(
    keyword: str,
    *,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    jan: Optional[str] = None,
    sort: str = "-review_count",    # -review_count, +price, -price, -score
    hits: int = 30,
    offset: int = 1,
    in_stock: bool = True,
    max_pages: int = 1,
    exclude_random: bool = True,
) -> list[YahooItem]:
    """Yahoo!ショッピングを検索。keyword か jan のどちらかを指定。"""
    if not YAHOO_APP_ID:
        raise YahooAPIError(
            "YAHOO_APP_ID が未設定です。.env に登録してください。\n"
            "取得: https://e.developer.yahoo.co.jp/register (無料)"
        )
    if not keyword and not jan:
        raise YahooAPIError("keyword または jan のどちらかを指定してください")

    results: list[YahooItem] = []
    for p in range(max_pages):
        _throttle()
        params = {
            "appid": YAHOO_APP_ID,
            "sort": sort,
            "results": hits,
            "start": offset + p * hits,
        }
        if keyword:
            params["query"] = keyword
        if jan:
            params["jan_code"] = jan
        if min_price is not None:
            params["price_from"] = min_price
        if max_price is not None:
            params["price_to"] = max_price
        if in_stock:
            params["in_stock"] = "true"

        resp = requests.get(API_URL, params=params, timeout=15)
        if resp.status_code != 200:
            raise YahooAPIError(f"API error {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        hits_list = data.get("hits") or []
        if not hits_list:
            break

        for it in hits_list:
            title = it.get("name", "")
            if exclude_random and _is_random_item(title):
                continue
            shipping = it.get("shipping") or {}
            point = it.get("point") or {}
            seller = it.get("seller") or {}
            review = it.get("review") or {}
            image = it.get("image") or {}
            results.append(YahooItem(
                item_code=str(it.get("code", "")),
                jan=it.get("janCode") or None,
                title=title,
                price=int(it.get("price", 0)),
                premium_price=int(it["premiumPrice"]) if it.get("premiumPrice") else None,
                shop_name=seller.get("name", ""),
                url=it.get("url", ""),
                image_url=image.get("medium") or image.get("small", ""),
                shipping_free=(shipping.get("code") == 2),
                point_amount=int(point.get("amount", 0) or 0),
                review_avg=float(review.get("rate", 0) or 0),
                review_count=int(review.get("count", 0) or 0),
                raw=it,
            ))
        if len(hits_list) < hits:
            break
    return results
