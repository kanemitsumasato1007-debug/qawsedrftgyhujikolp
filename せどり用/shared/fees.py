"""販路別の手数料計算。

料率はユーザー側で `shared/config.py` または本ファイルの定数を更新する前提。
2025年時点の公開情報を元にした概算値。正確な請求値は必ず各販路の最新情報で検算すること。
"""
from dataclasses import dataclass
from math import floor

# ---- 販売手数料率(販売価格に対する%)----
# Amazon: カテゴリ別。最低手数料 30円/点
AMAZON_RATE = {
    "ホビー": 0.10,
    "ゲーム": 0.15,
    "美容": 0.10,      # 売価3,000円以下は10%、超過分は8%(簡略化のため10%固定)
    "アパレル": 0.12,
    "その他": 0.15,
}
AMAZON_MIN_FEE = 30

# メルカリ: 一律10%
MERCARI_RATE = 0.10

# ヤフオク: Yahoo!プレミアム会員 8.8%、非会員 10%
YAHOO_RATE = 0.10
YAHOO_PREMIUM_RATE = 0.088

# ラクマ: 6.0%(決済手数料込み想定で6.6%運用するユーザーも)
RAKUMA_RATE = 0.06


@dataclass
class ProfitBreakdown:
    sale_price: int
    platform_fee: int
    fba_fee: int
    shipping_out: int
    other_cost: int
    cost_of_goods: int       # 仕入原価(送料・ポイント還元込み)
    profit: int              # 粗利
    roi: float               # 投資対効果 profit / cost_of_goods
    margin: float            # 利益率 profit / sale_price

    def pretty(self) -> str:
        return (
            f"販売価格   : {self.sale_price:>8,}円\n"
            f"販売手数料 : -{self.platform_fee:>7,}円\n"
            f"FBA手数料  : -{self.fba_fee:>7,}円\n"
            f"出荷送料   : -{self.shipping_out:>7,}円\n"
            f"その他経費 : -{self.other_cost:>7,}円\n"
            f"仕入原価   : -{self.cost_of_goods:>7,}円\n"
            f"---------------------------\n"
            f"粗利       : {self.profit:>8,}円\n"
            f"ROI        : {self.roi*100:>7.1f}%\n"
            f"利益率     : {self.margin*100:>7.1f}%"
        )


def platform_fee(channel: str, sale_price: int, category: str = "その他",
                 yahoo_premium: bool = True) -> int:
    """販路別の販売手数料を返す(円、切り捨て)。"""
    if channel in ("Amazon", "Amazon FBA"):
        rate = AMAZON_RATE.get(category, AMAZON_RATE["その他"])
        return max(floor(sale_price * rate), AMAZON_MIN_FEE)
    if channel == "メルカリ":
        return floor(sale_price * MERCARI_RATE)
    if channel == "ヤフオク":
        rate = YAHOO_PREMIUM_RATE if yahoo_premium else YAHOO_RATE
        return floor(sale_price * rate)
    if channel == "ラクマ":
        return floor(sale_price * RAKUMA_RATE)
    return 0


def calc_profit(
    sale_price: int,
    quantity: int,
    unit_purchase_price: int,
    channel: str,
    category: str = "その他",
    fba_fee: int = 0,
    shipping_out: int = 0,
    shipping_in: int = 0,
    point_back: int = 0,
    other_cost: int = 0,
    yahoo_premium: bool = True,
    override_platform_fee: int | None = None,
) -> ProfitBreakdown:
    """販売記録1件分の粗利を計算する。

    - 仕入原価 = 単価×数量 + 仕入送料 − ポイント還元
    - 販売側合計 = 販売価格×数量
    - 手数料は1件あたりで計算し、数量倍する(FBA手数料・出荷送料も同様)
    """
    sale_total = sale_price * quantity
    cost_of_goods = unit_purchase_price * quantity + shipping_in - point_back

    if override_platform_fee is not None:
        pf = override_platform_fee
    else:
        pf = platform_fee(channel, sale_price, category, yahoo_premium) * quantity

    fba_total = fba_fee * quantity
    ship_total = shipping_out * quantity
    other_total = other_cost * quantity

    profit = sale_total - pf - fba_total - ship_total - other_total - cost_of_goods
    roi = profit / cost_of_goods if cost_of_goods > 0 else 0.0
    margin = profit / sale_total if sale_total > 0 else 0.0

    return ProfitBreakdown(
        sale_price=sale_total,
        platform_fee=pf,
        fba_fee=fba_total,
        shipping_out=ship_total,
        other_cost=other_total,
        cost_of_goods=cost_of_goods,
        profit=profit,
        roi=roi,
        margin=margin,
    )


def breakeven_sale_price(
    unit_purchase_price: int,
    channel: str,
    category: str = "その他",
    fba_fee: int = 0,
    shipping_out: int = 0,
    shipping_in: int = 0,
    point_back: int = 0,
    other_cost: int = 0,
    yahoo_premium: bool = True,
) -> int:
    """粗利0円になる販売価格(損益分岐点)を返す。

    手数料は率ベースなので: price = (fixed_costs) / (1 - rate)
    """
    if channel in ("Amazon", "Amazon FBA"):
        rate = AMAZON_RATE.get(category, AMAZON_RATE["その他"])
    elif channel == "メルカリ":
        rate = MERCARI_RATE
    elif channel == "ヤフオク":
        rate = YAHOO_PREMIUM_RATE if yahoo_premium else YAHOO_RATE
    elif channel == "ラクマ":
        rate = RAKUMA_RATE
    else:
        rate = 0.0

    fixed = unit_purchase_price + shipping_in - point_back + fba_fee + shipping_out + other_cost
    if rate >= 1.0:
        return fixed
    return int(fixed / (1 - rate)) + 1
