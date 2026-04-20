"""Amazon価格の取得抽象化。

Keepa契約前は ManualProvider(Sheets内の手動登録価格を返す)を使い、
契約後は KeepaProvider に差し替えるだけで済むようにする。
"""
from dataclasses import dataclass
from typing import Optional, Protocol

from shared import sheets
from shared.config import KEEPA_API_KEY


@dataclass
class AmazonPrice:
    asin: str
    price: int
    sales_rank: Optional[int]
    fba_fee: Optional[int]
    fetched_at: str


class AmazonPriceProvider(Protocol):
    def get_price(self, asin: str) -> Optional[AmazonPrice]: ...


class ManualProvider:
    """ユーザーが手動登録した価格を price_history から返す暫定プロバイダ。"""
    name = "manual"

    def get_price(self, asin: str) -> Optional[AmazonPrice]:
        prod = sheets.find_one("products", asin=asin)
        if not prod:
            return None
        history = sheets.find_all("price_history", product_id=int(prod["id"]), source="Amazon")
        if not history:
            return None
        latest = max(history, key=lambda h: h.get("fetched_at", ""))
        return AmazonPrice(
            asin=asin, price=int(latest["price"]),
            sales_rank=int(latest["sales_rank"]) if latest.get("sales_rank") else None,
            fba_fee=None, fetched_at=latest.get("fetched_at", ""),
        )


class KeepaProvider:
    """Keepa API 連携(契約後に実装を埋める)。"""
    name = "keepa"

    def __init__(self, api_key: str = KEEPA_API_KEY):
        self.api_key = api_key

    def get_price(self, asin: str) -> Optional[AmazonPrice]:
        if not self.api_key:
            raise NotImplementedError("KEEPA_API_KEY 未設定。Keepa契約後に .env へ設定してください。")
        raise NotImplementedError("KeepaProvider 未実装。契約確定後に実装する。")


def get_provider(name: str = "auto") -> AmazonPriceProvider:
    if name == "keepa":
        return KeepaProvider()
    if name == "manual":
        return ManualProvider()
    if KEEPA_API_KEY:
        return KeepaProvider()
    return ManualProvider()


def save_manual_price(asin: str, price: int, sales_rank: Optional[int] = None) -> int:
    prod = sheets.find_one("products", asin=asin)
    if not prod:
        raise ValueError(f"ASIN={asin} を持つ商品がマスターに未登録です。先に product add で登録してください。")
    sheets.append("price_history", {
        "product_id": int(prod["id"]), "source": "Amazon",
        "price": price, "sales_rank": sales_rank or "",
    })
    return int(prod["id"])
