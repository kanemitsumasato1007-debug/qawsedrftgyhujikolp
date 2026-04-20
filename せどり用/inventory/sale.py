import click
from tabulate import tabulate
from shared import sheets
from shared.config import SALE_CHANNELS
from shared.fees import platform_fee, calc_profit


@click.group(help="販売記録")
def sale():
    pass


def _sold_quantity(purchase_id: int) -> int:
    sales = sheets.find_all("sales", purchase_id=purchase_id)
    return sum(int(s.get("quantity") or 0) for s in sales)


@sale.command("add", help="販売を記録(販売手数料は未指定なら自動計算)")
@click.option("--purchase-id", required=True, type=int)
@click.option("--date", "sale_date", required=True, help="YYYY-MM-DD")
@click.option("--channel", required=True, type=click.Choice(SALE_CHANNELS))
@click.option("--price", "sale_price", required=True, type=int, help="販売価格(税込)")
@click.option("--qty", "quantity", required=True, type=int)
@click.option("--platform-fee", "platform_fee_override", default=None, type=int,
              help="販売手数料(円,合計)。省略時は自動計算")
@click.option("--fba-fee", default=0, type=int, help="FBA配送代行手数料(1点あたり)")
@click.option("--shipping", "shipping_out", default=0, type=int, help="出荷送料(1点あたり)")
@click.option("--other", "other_cost", default=0, type=int, help="その他経費(1点あたり)")
@click.option("--memo", default=None)
def add(purchase_id, sale_date, channel, sale_price, quantity,
        platform_fee_override, fba_fee, shipping_out, other_cost, memo):
    p = sheets.find_by_id("purchases", purchase_id)
    if not p:
        raise click.ClickException(f"purchase_id={purchase_id} が存在しません")
    prod = sheets.find_by_id("products", int(p["product_id"]))
    if not prod:
        raise click.ClickException(f"仕入 {purchase_id} の商品マスターが見つかりません")

    sold = _sold_quantity(purchase_id)
    remaining = int(p["quantity"]) - sold
    if quantity > remaining:
        raise click.ClickException(f"残数量超過: 残 {remaining} に対して {quantity} 売ろうとしています")

    pf = (platform_fee_override if platform_fee_override is not None
          else platform_fee(channel, sale_price, prod["category"]) * quantity)

    new_id = sheets.append("sales", {
        "purchase_id": purchase_id, "sale_date": sale_date, "channel": channel,
        "sale_price": sale_price, "quantity": quantity,
        "platform_fee": pf, "fba_fee": fba_fee * quantity,
        "shipping_out": shipping_out * quantity, "other_cost": other_cost * quantity,
        "memo": memo,
    })

    prorate_ship = round(int(p.get("shipping_in") or 0) * quantity / int(p["quantity"]))
    prorate_point = round(int(p.get("point_back") or 0) * quantity / int(p["quantity"]))
    breakdown = calc_profit(
        sale_price=sale_price, quantity=quantity,
        unit_purchase_price=int(p["unit_price"]),
        channel=channel, category=prod["category"],
        fba_fee=fba_fee, shipping_out=shipping_out,
        shipping_in=prorate_ship, point_back=prorate_point,
        other_cost=other_cost, override_platform_fee=pf,
    )
    click.echo(f"販売登録: id={new_id}")
    click.echo(breakdown.pretty())


@sale.command("list", help="販売一覧")
@click.option("--channel", type=click.Choice(SALE_CHANNELS), default=None)
@click.option("--since", default=None, help="YYYY-MM-DD 以降")
@click.option("--until", default=None, help="YYYY-MM-DD 以前")
def list_sales(channel, since, until):
    sales = sheets.all_records("sales")
    purchases_idx = {int(p["id"]): p for p in sheets.all_records("purchases")}
    products_idx = {int(pr["id"]): pr for pr in sheets.all_records("products")}
    rows = []
    for s in sales:
        if channel and s["channel"] != channel:
            continue
        if since and s["sale_date"] < since:
            continue
        if until and s["sale_date"] > until:
            continue
        p = purchases_idx.get(int(s["purchase_id"]), {})
        prod = products_idx.get(int(p.get("product_id") or 0), {})
        rows.append({
            "id": s["id"], "date": s["sale_date"],
            "product": prod.get("name", ""), "channel": s["channel"],
            "sale_price": s["sale_price"], "quantity": s["quantity"],
            "platform_fee": s["platform_fee"], "fba_fee": s["fba_fee"],
            "shipping_out": s["shipping_out"], "other_cost": s["other_cost"],
        })
    if not rows:
        click.echo("(該当なし)")
        return
    rows.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    click.echo(tabulate(rows, headers="keys", tablefmt="github"))
