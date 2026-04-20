import click
from tabulate import tabulate
from shared import sheets
from shared.config import PURCHASE_SOURCES


@click.group(help="仕入れ記録")
def purchase():
    pass


def _sold_quantity(purchase_id: int) -> int:
    sales = sheets.find_all("sales", purchase_id=purchase_id)
    return sum(int(s.get("quantity") or 0) for s in sales)


@purchase.command("add", help="仕入れを記録")
@click.option("--product-id", required=True, type=int)
@click.option("--date", "purchase_date", required=True, help="YYYY-MM-DD")
@click.option("--source", required=True, type=click.Choice(PURCHASE_SOURCES))
@click.option("--store", "store_name", default=None, help="店舗名/出品者名")
@click.option("--price", "unit_price", required=True, type=int, help="税込単価(円)")
@click.option("--qty", "quantity", required=True, type=int)
@click.option("--shipping", "shipping_in", default=0, type=int, help="仕入れ送料(円)")
@click.option("--point", "point_back", default=0, type=int, help="ポイント還元(円相当)")
@click.option("--memo", default=None)
def add(product_id, purchase_date, source, store_name, unit_price, quantity,
        shipping_in, point_back, memo):
    if not sheets.find_by_id("products", product_id):
        raise click.ClickException(f"product_id={product_id} が存在しません")
    new_id = sheets.append("purchases", {
        "product_id": product_id, "purchase_date": purchase_date, "source": source,
        "store_name": store_name, "unit_price": unit_price, "quantity": quantity,
        "shipping_in": shipping_in, "point_back": point_back, "memo": memo,
    })
    total = unit_price * quantity + shipping_in - point_back
    click.echo(f"仕入登録: id={new_id} 仕入原価合計={total:,}円")


@purchase.command("list", help="仕入れ一覧")
@click.option("--product-id", type=int, default=None)
@click.option("--source", type=click.Choice(PURCHASE_SOURCES), default=None)
@click.option("--unsold", is_flag=True, help="未販売分のみ")
def list_purchases(product_id, source, unsold):
    purchases = sheets.all_records("purchases")
    products_idx = {int(p["id"]): p for p in sheets.all_records("products")}
    rows = []
    for p in purchases:
        if product_id and int(p["product_id"]) != product_id:
            continue
        if source and p["source"] != source:
            continue
        sold = _sold_quantity(int(p["id"]))
        remaining = int(p["quantity"]) - sold
        if unsold and remaining <= 0:
            continue
        prod = products_idx.get(int(p["product_id"]), {})
        rows.append({
            "id": p["id"], "date": p["purchase_date"],
            "product": prod.get("name", ""), "source": p["source"],
            "store": p.get("store_name", ""), "unit_price": p["unit_price"],
            "quantity": p["quantity"], "sold": sold, "remaining": remaining,
        })
    if not rows:
        click.echo("(該当なし)")
        return
    rows.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    click.echo(tabulate(rows, headers="keys", tablefmt="github"))


@purchase.command("delete", help="仕入を削除(販売記録がある場合は不可)")
@click.argument("purchase_id", type=int)
def delete(purchase_id):
    if _sold_quantity(purchase_id) > 0:
        raise click.ClickException(f"purchase_id={purchase_id} は販売済みのため削除不可")
    if sheets.delete_by_id("purchases", purchase_id):
        click.echo(f"仕入 id={purchase_id} を削除しました")
    else:
        click.echo(f"id={purchase_id} は存在しません")
