"""せどり管理CLIエントリポイント。

使い方:
    python sedori.py init                     # DB初期化
    python sedori.py product add --name "..." --category ホビー
    python sedori.py purchase add ...
    python sedori.py sale add ...
    python sedori.py report monthly
    python sedori.py calc --price 3980 --cost 1500 --channel "Amazon FBA" --category ゲーム
"""
import sys
import click

# Windows コンソールの文字化け対策
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from shared import sheets
from shared.fees import calc_profit, breakeven_sale_price
from shared.config import SALE_CHANNELS, CATEGORIES
from inventory.products import products
from inventory.purchase import purchase
from inventory.sale import sale
from inventory.report import report
from research.cli import research


@click.group()
def cli():
    """せどり管理ツール"""


@cli.command("init", help="Spreadsheetにタブとヘッダを自動生成")
def cmd_init():
    created = sheets.init_sheets()
    sheets.init_dashboard()
    if created:
        click.echo(f"タブを作成: {', '.join(created)}")
    else:
        click.echo("全タブ既存(ヘッダを最新版に同期しました)")
    click.echo("dashboard タブを更新しました")


@cli.group(help="Google Sheets バックエンド操作")
def sheets_cmd():
    pass


@sheets_cmd.command("init", help="Spreadsheet にタブとヘッダを作成(同: sedori init)")
def sheets_init():
    created = sheets.init_sheets()
    sheets.init_dashboard()
    if created:
        click.echo(f"タブを作成: {', '.join(created)}")
    else:
        click.echo("全タブ既存(ヘッダを最新版に同期しました)")
    click.echo("dashboard タブを更新しました")


@sheets_cmd.command("info", help="接続先Spreadsheetの情報を表示")
def sheets_info():
    sh = sheets._spreadsheet()
    click.echo(f"Spreadsheet: {sh.title}")
    click.echo(f"URL: {sh.url}")
    click.echo("タブ:")
    for w in sh.worksheets():
        click.echo(f"  - {w.title} ({w.row_count}行 x {w.col_count}列)")


@cli.command("calc", help="仕入候補の損益シミュレーション")
@click.option("--price", "sale_price", required=True, type=int, help="想定販売価格(税込)")
@click.option("--cost", "unit_cost", required=True, type=int, help="仕入単価(税込)")
@click.option("--channel", required=True, type=click.Choice(SALE_CHANNELS))
@click.option("--category", type=click.Choice(CATEGORIES), default="その他")
@click.option("--qty", default=1, type=int)
@click.option("--fba-fee", default=0, type=int)
@click.option("--shipping-in", default=0, type=int)
@click.option("--shipping-out", default=0, type=int)
@click.option("--point", default=0, type=int, help="ポイント還元(円)")
@click.option("--other", default=0, type=int)
def cmd_calc(sale_price, unit_cost, channel, category, qty, fba_fee,
             shipping_in, shipping_out, point, other):
    b = calc_profit(
        sale_price=sale_price, quantity=qty, unit_purchase_price=unit_cost,
        channel=channel, category=category, fba_fee=fba_fee,
        shipping_in=shipping_in, shipping_out=shipping_out,
        point_back=point, other_cost=other,
    )
    click.echo(b.pretty())
    be = breakeven_sale_price(
        unit_purchase_price=unit_cost, channel=channel, category=category,
        fba_fee=fba_fee, shipping_in=shipping_in, shipping_out=shipping_out,
        point_back=point, other_cost=other,
    )
    click.echo(f"\n損益分岐販売価格: {be:,}円")


cli.add_command(products, name="product")
cli.add_command(purchase, name="purchase")
cli.add_command(sale, name="sale")
cli.add_command(report, name="report")
cli.add_command(research, name="research")
cli.add_command(sheets_cmd, name="sheets")


if __name__ == "__main__":
    cli()
