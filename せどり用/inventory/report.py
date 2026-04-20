import click
import csv
from collections import defaultdict
from datetime import datetime
from tabulate import tabulate

from shared import sheets


@click.group(help="集計レポート")
def report():
    pass


def _enriched_sales():
    """sales を purchases/products と結合し、粗利を計算した行を返す。"""
    sales = sheets.all_records("sales")
    purchases_idx = {int(p["id"]): p for p in sheets.all_records("purchases")}
    products_idx = {int(pr["id"]): pr for pr in sheets.all_records("products")}
    out = []
    for s in sales:
        p = purchases_idx.get(int(s["purchase_id"]))
        if not p:
            continue
        prod = products_idx.get(int(p["product_id"]), {})
        qty = int(s["quantity"])
        sale_total = int(s["sale_price"]) * qty
        prorate_ship = round(int(p.get("shipping_in") or 0) * qty / int(p["quantity"]))
        prorate_point = round(int(p.get("point_back") or 0) * qty / int(p["quantity"]))
        cost = int(p["unit_price"]) * qty + prorate_ship - prorate_point
        fees = (int(s.get("platform_fee") or 0) + int(s.get("fba_fee") or 0)
                + int(s.get("shipping_out") or 0) + int(s.get("other_cost") or 0))
        profit = sale_total - fees - cost
        out.append({
            "sale_id": s["id"], "date": s["sale_date"],
            "product": prod.get("name", ""), "category": prod.get("category", ""),
            "channel": s["channel"],
            "sales": sale_total, "cost": cost, "fees": fees, "profit": profit,
        })
    return out


@report.command("monthly", help="月次サマリ")
@click.option("--year", type=int, default=None, help="YYYY(省略で全期間)")
def monthly(year):
    rows = _enriched_sales()
    if year:
        rows = [r for r in rows if r["date"].startswith(str(year))]
    agg = defaultdict(lambda: {"sales": 0, "cost": 0, "fees": 0, "profit": 0, "count": 0})
    for r in rows:
        month = (r["date"] or "")[:7]
        if not month:
            continue
        a = agg[month]
        a["sales"] += r["sales"]; a["cost"] += r["cost"]
        a["fees"] += r["fees"]; a["profit"] += r["profit"]; a["count"] += 1
    if not agg:
        click.echo("(該当なし)")
        return
    out = [{"month": m, **v} for m, v in sorted(agg.items(), reverse=True)]
    click.echo(tabulate(out, headers="keys", tablefmt="github"))


@report.command("by-channel", help="販路別サマリ")
@click.option("--since", default=None)
@click.option("--until", default=None)
def by_channel(since, until):
    rows = _enriched_sales()
    if since:
        rows = [r for r in rows if r["date"] >= since]
    if until:
        rows = [r for r in rows if r["date"] <= until]
    agg = defaultdict(lambda: {"sales": 0, "cost": 0, "fees": 0, "profit": 0, "cnt": 0})
    for r in rows:
        a = agg[r["channel"]]
        a["sales"] += r["sales"]; a["cost"] += r["cost"]
        a["fees"] += r["fees"]; a["profit"] += r["profit"]; a["cnt"] += 1
    if not agg:
        click.echo("(該当なし)")
        return
    out = [{"channel": c, **v} for c, v in sorted(agg.items(), key=lambda x: -x[1]["profit"])]
    click.echo(tabulate(out, headers="keys", tablefmt="github"))


@report.command("by-category", help="カテゴリ別サマリ")
def by_category():
    rows = _enriched_sales()
    agg = defaultdict(lambda: {"sales": 0, "profit": 0, "cnt": 0, "roi_sum": 0.0, "roi_cnt": 0})
    for r in rows:
        a = agg[r["category"] or "未分類"]
        a["sales"] += r["sales"]; a["profit"] += r["profit"]; a["cnt"] += 1
        if r["cost"] > 0:
            a["roi_sum"] += r["profit"] / r["cost"]; a["roi_cnt"] += 1
    if not agg:
        click.echo("(該当なし)")
        return
    out = []
    for cat, v in sorted(agg.items(), key=lambda x: -x[1]["profit"]):
        avg_roi = (v["roi_sum"] / v["roi_cnt"] * 100) if v["roi_cnt"] else 0
        out.append({"category": cat, "sales": v["sales"], "profit": v["profit"],
                    "cnt": v["cnt"], "avg_roi_pct": round(avg_roi, 1)})
    click.echo(tabulate(out, headers="keys", tablefmt="github"))


@report.command("inventory", help="未販売在庫(滞留含む)")
def inventory():
    purchases = sheets.all_records("purchases")
    sales = sheets.all_records("sales")
    products_idx = {int(pr["id"]): pr for pr in sheets.all_records("products")}
    sold_by_purchase = defaultdict(int)
    for s in sales:
        sold_by_purchase[int(s["purchase_id"])] += int(s["quantity"])
    today = datetime.now().date()
    rows = []
    for p in purchases:
        sold = sold_by_purchase.get(int(p["id"]), 0)
        remaining = int(p["quantity"]) - sold
        if remaining <= 0:
            continue
        try:
            d = datetime.strptime(p["purchase_date"], "%Y-%m-%d").date()
            days_held = (today - d).days
        except Exception:
            days_held = None
        prod = products_idx.get(int(p["product_id"]), {})
        rows.append({
            "product_id": p["product_id"], "product": prod.get("name", ""),
            "category": prod.get("category", ""),
            "purchase_id": p["id"], "purchase_date": p["purchase_date"],
            "source": p["source"], "unit_price": p["unit_price"],
            "remaining": remaining, "days_held": days_held,
        })
    if not rows:
        click.echo("(在庫なし)")
        return
    rows.sort(key=lambda r: -(r["days_held"] or 0))
    click.echo(tabulate(rows, headers="keys", tablefmt="github"))


@report.command("export", help="詳細CSV出力(確定申告用)")
@click.option("--out", default="sales_export.csv", help="出力ファイル名")
def export(out):
    rows = _enriched_sales()
    if not rows:
        click.echo("(データなし)")
        return
    rows.sort(key=lambda r: r["date"])
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    click.echo(f"{len(rows)}件を {out} に出力しました")
