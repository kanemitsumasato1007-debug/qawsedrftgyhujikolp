import click
from tabulate import tabulate
from shared import sheets
from shared.config import CATEGORIES


@click.group(help="商品マスター操作")
def products():
    pass


@products.command("add", help="商品を登録")
@click.option("--name", required=True, help="商品名")
@click.option("--category", required=True, type=click.Choice(CATEGORIES), help="カテゴリ")
@click.option("--jan", default=None, help="JANコード")
@click.option("--asin", default=None, help="Amazon ASIN")
@click.option("--sku", default=None, help="自分の管理SKU")
@click.option("--url-amazon", default=None)
@click.option("--url-rakuten", default=None)
@click.option("--url-mercari", default=None)
@click.option("--url-yahoo", default=None)
@click.option("--memo", default=None)
def add(name, category, jan, asin, sku, url_amazon, url_rakuten, url_mercari, url_yahoo, memo):
    new_id = sheets.append("products", {
        "name": name, "category": category, "jan": jan, "asin": asin, "sku": sku,
        "url_amazon": url_amazon, "url_rakuten": url_rakuten,
        "url_mercari": url_mercari, "url_yahoo": url_yahoo, "memo": memo,
    })
    click.echo(f"商品登録: id={new_id} {name} ({category})")


@products.command("list", help="商品一覧")
@click.option("--category", type=click.Choice(CATEGORIES), default=None)
@click.option("--q", default=None, help="商品名部分一致検索")
def list_products(category, q):
    rows = sheets.all_records("products")
    if category:
        rows = [r for r in rows if r["category"] == category]
    if q:
        rows = [r for r in rows if q in (r.get("name") or "")]
    if not rows:
        click.echo("(該当なし)")
        return
    rows.sort(key=lambda r: int(r["id"]), reverse=True)
    display = [{k: r.get(k, "") for k in ("id", "name", "category", "jan", "asin", "sku")}
               for r in rows]
    click.echo(tabulate(display, headers="keys", tablefmt="github"))


@products.command("delete", help="商品を削除")
@click.argument("product_id", type=int)
def delete(product_id):
    if sheets.delete_by_id("products", product_id):
        click.echo(f"商品 id={product_id} を削除しました")
    else:
        click.echo(f"id={product_id} は存在しません")
