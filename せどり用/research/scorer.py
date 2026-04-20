"""仕入れ候補の差額スコアリング。

楽天価格(or他販路仕入価格) × Amazon相場(手動/Keepa) × 手数料計算
→ 粗利/ROI/推奨度を算出
"""
from dataclasses import dataclass
from typing import Optional

from shared.fees import calc_profit, breakeven_sale_price, ProfitBreakdown


ASSUMED_SHIPPING_IF_UNKNOWN = 500   # 送料別の場合の暫定仕入送料(円)


@dataclass
class Candidate:
    title: str
    source: str                     # '楽天' 等
    shop_name: str
    url: str
    purchase_price: int             # 楽天価格(税込)
    effective_cost: int             # ポイント還元後の実質仕入原価
    point_back: int
    shipping_in_estimate: int
    amazon_price: Optional[int]     # None なら未マッチ
    sales_rank: Optional[int]
    category: str
    breakdown: Optional[ProfitBreakdown]
    breakeven_amazon: int           # Amazon側の損益分岐販売価格
    notes: list[str]

    @property
    def roi(self) -> float:
        return self.breakdown.roi if self.breakdown else 0.0

    @property
    def profit(self) -> int:
        return self.breakdown.profit if self.breakdown else 0


def _estimated_fba_fee(category: str, price: int) -> int:
    """FBA手数料の概算(小型標準サイズ目安)。実データで補正推奨。"""
    if category == "アパレル":
        return 434
    if price < 1000:
        return 293
    if price < 3000:
        return 350
    if price < 10000:
        return 421
    return 500


def score_rakuten_item(
    *,
    title: str,
    purchase_price: int,
    point_rate: float,
    postage_flag: int,          # 0=送料込み, 1=送料別
    shop_name: str,
    url: str,
    category: str,
    amazon_price: Optional[int],
    sales_rank: Optional[int] = None,
    fba_fee: Optional[int] = None,
    source_label: str = "楽天",
) -> Candidate:
    point_back = int(purchase_price * point_rate / 100)
    shipping_in = 0 if postage_flag == 0 else ASSUMED_SHIPPING_IF_UNKNOWN
    effective_cost = purchase_price + shipping_in - point_back

    notes = []
    if postage_flag == 1:
        notes.append(f"送料別: 仮に {ASSUMED_SHIPPING_IF_UNKNOWN}円加算")
    if point_rate > 1:
        notes.append(f"ポイント {point_rate}倍 ({point_back}円相当)")

    estimated_fba = fba_fee if fba_fee is not None else _estimated_fba_fee(category, purchase_price)

    breakeven = breakeven_sale_price(
        unit_purchase_price=purchase_price,
        channel="Amazon FBA",
        category=category,
        fba_fee=estimated_fba,
        shipping_in=shipping_in,
        point_back=point_back,
    )

    breakdown = None
    if amazon_price is not None:
        breakdown = calc_profit(
            sale_price=amazon_price,
            quantity=1,
            unit_purchase_price=purchase_price,
            channel="Amazon FBA",
            category=category,
            fba_fee=estimated_fba,
            shipping_in=shipping_in,
            point_back=point_back,
        )

    return Candidate(
        title=title,
        source=source_label,
        shop_name=shop_name,
        url=url,
        purchase_price=purchase_price,
        effective_cost=effective_cost,
        point_back=point_back,
        shipping_in_estimate=shipping_in,
        amazon_price=amazon_price,
        sales_rank=sales_rank,
        category=category,
        breakdown=breakdown,
        breakeven_amazon=breakeven,
        notes=notes,
    )
