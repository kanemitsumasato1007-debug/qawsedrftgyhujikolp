import click
from datetime import datetime, timedelta
from tabulate import tabulate

from shared import sheets
from shared.config import CATEGORIES
from research import rakuten, yahoo, amazon_provider
from research.scorer import score_rakuten_item


@click.group(help="リサーチ(仕入候補抽出・Amazon相場比較)")
def research():
    pass


# ---------- 楽天検索 ----------
@research.command("rakuten-search", help="楽天市場を検索して候補を保存・スコアリング")
@click.argument("keyword")
@click.option("--category", type=click.Choice(CATEGORIES), default="その他",
              help="Amazon側のカテゴリ(手数料計算に使用)")
@click.option("--min", "min_price", type=int, default=None)
@click.option("--max", "max_price", type=int, default=None)
@click.option("--sort", default="-reviewCount",
              type=click.Choice(["-reviewCount", "+itemPrice", "-itemPrice", "+updateTimestamp"]))
@click.option("--pages", default=1, type=int, help="取得ページ数(1ページ=30件)")
@click.option("--min-roi", type=float, default=None, help="候補表示のROI下限(%)")
@click.option("--save/--no-save", default=True, help="sourced_items に保存するか")
@click.option("--include-random", is_flag=True,
              help="福袋/ガチャ/オリパ等の運要素商品も含める(既定は除外)")
def rakuten_search(keyword, category, min_price, max_price, sort, pages, min_roi, save, include_random):
    try:
        items = rakuten.search(
            keyword, min_price=min_price, max_price=max_price,
            sort=sort, max_pages=pages, exclude_random=not include_random,
        )
    except rakuten.RakutenAPIError as e:
        raise click.ClickException(str(e))

    if not items:
        click.echo("(ヒットなし)")
        return

    provider = amazon_provider.get_provider()

    # 既存 sourced_items から楽天item_code→product_id のマッピングを作成
    existing_sourced = sheets.all_records("sourced_items")
    code_to_product = {
        si.get("source_item_id"): int(si["product_id"])
        for si in existing_sourced
        if si.get("source") == "楽天" and si.get("product_id")
    }
    products_by_id = {int(p["id"]): p for p in sheets.all_records("products")}

    candidates = []
    rows_to_save = []
    history_to_save = []

    for it in items:
        product_id = code_to_product.get(it.item_code)
        product = products_by_id.get(product_id) if product_id else None
        amazon_price = None
        sales_rank = None
        if product and product.get("asin"):
            ap = provider.get_price(product["asin"])
            if ap:
                amazon_price = ap.price
                sales_rank = ap.sales_rank

        cand = score_rakuten_item(
            title=it.title, purchase_price=it.price,
            point_rate=it.point_rate, postage_flag=it.postage_flag,
            shop_name=it.shop_name, url=it.url,
            category=category, amazon_price=amazon_price, sales_rank=sales_rank,
        )
        candidates.append((it, cand, product_id))

        if save:
            rows_to_save.append({
                "source": "楽天", "source_item_id": it.item_code,
                "product_id": product_id or "", "title": it.title,
                "price": it.price, "shop_name": it.shop_name,
                "url": it.url, "image_url": it.image_url,
                "postage_flag": it.postage_flag, "point_rate": it.point_rate,
                "review_avg": it.review_avg, "review_count": it.review_count,
                "query": keyword,
            })
            if product_id:
                history_to_save.append({
                    "product_id": product_id, "source": "楽天",
                    "price": it.price, "sales_rank": "",
                })

    saved_ids: list[int] = []
    if save and rows_to_save:
        saved_ids = sheets.append_many("sourced_items", rows_to_save)
        if history_to_save:
            sheets.append_many("price_history", history_to_save)

    filtered = candidates
    if min_roi is not None:
        filtered = [(it, c, pid) for it, c, pid in candidates
                    if c.breakdown and c.roi * 100 >= min_roi]

    if not filtered:
        click.echo(f"(ROI {min_roi}% 以上の候補なし。全{len(candidates)}件のうちAmazon相場未登録が多い可能性あり)")
    else:
        rows = []
        for i, (_it, c, _pid) in enumerate(filtered):
            rows.append({
                "#": i + 1, "shop": c.shop_name[:12], "title": c.title[:40],
                "楽天": f"{c.purchase_price:,}", "実質": f"{c.effective_cost:,}",
                "Amazon": f"{c.amazon_price:,}" if c.amazon_price else "未登録",
                "損益分岐": f"{c.breakeven_amazon:,}",
                "粗利": f"{c.profit:+,}" if c.breakdown else "-",
                "ROI%": f"{c.roi*100:.1f}" if c.breakdown else "-",
            })
        click.echo(tabulate(rows, headers="keys", tablefmt="github"))

    click.echo(f"\n取得 {len(items)} 件 / 保存 {len(saved_ids)} 件 / キーワード: {keyword}")
    if saved_ids:
        click.echo(f"sourced_items ID範囲: {saved_ids[0]} - {saved_ids[-1]}")
        click.echo("ASINを紐づけるには: python sedori.py research link --sourced-id <id> --asin <ASIN>")


# ---------- Yahoo!ショッピング検索 ----------
@research.command("yahoo-search", help="Yahoo!ショッピングを検索して候補を保存・スコアリング")
@click.argument("keyword")
@click.option("--category", type=click.Choice(CATEGORIES), default="その他")
@click.option("--min", "min_price", type=int, default=None)
@click.option("--max", "max_price", type=int, default=None)
@click.option("--jan", default=None, help="JANコード指定検索(他パラメータ不要)")
@click.option("--sort", default="-review_count",
              type=click.Choice(["-review_count", "+price", "-price", "-score"]))
@click.option("--pages", default=1, type=int, help="取得ページ数(1ページ=30件)")
@click.option("--min-roi", type=float, default=None)
@click.option("--save/--no-save", default=True)
@click.option("--include-random", is_flag=True,
              help="福袋/ガチャ/オリパ等の運要素商品も含める(既定は除外)")
def yahoo_search(keyword, category, min_price, max_price, jan, sort, pages, min_roi, save, include_random):
    try:
        items = yahoo.search(
            keyword if not jan else "", min_price=min_price, max_price=max_price,
            jan=jan, sort=sort, max_pages=pages, exclude_random=not include_random,
        )
    except yahoo.YahooAPIError as e:
        raise click.ClickException(str(e))
    if not items:
        click.echo("(ヒットなし)")
        return

    provider = amazon_provider.get_provider()

    # JANで既存商品をマッチング(Yahoo!はJANを返すので自動でできる)
    products = sheets.all_records("products")
    jan_to_product = {p.get("jan"): p for p in products if p.get("jan")}

    candidates = []
    rows_to_save = []
    history_to_save = []

    for it in items:
        prod = jan_to_product.get(it.jan) if it.jan else None
        amazon_price = None
        sales_rank = None
        if prod and prod.get("asin"):
            ap = provider.get_price(prod["asin"])
            if ap:
                amazon_price = ap.price
                sales_rank = ap.sales_rank

        # Yahoo!のポイント還元額 → ポイント倍率換算(仕入価格比)
        point_rate_equiv = (it.point_amount / it.price * 100) if it.price else 1
        # shipping_free=True なら postage_flag=0(送料込み)
        postage_flag = 0 if it.shipping_free else 1

        cand = score_rakuten_item(
            title=it.title, purchase_price=it.price,
            point_rate=max(1.0, point_rate_equiv),
            postage_flag=postage_flag,
            shop_name=it.shop_name, url=it.url,
            category=category,
            amazon_price=amazon_price, sales_rank=sales_rank,
            source_label="Yahoo!",
        )
        candidates.append((it, cand, int(prod["id"]) if prod else None))

        if save:
            rows_to_save.append({
                "source": "Yahoo!", "source_item_id": it.item_code,
                "product_id": int(prod["id"]) if prod else "",
                "asin": (prod or {}).get("asin", ""),
                "jan": it.jan or "",
                "title": it.title, "price": it.price,
                "shop_name": it.shop_name, "url": it.url, "image_url": it.image_url,
                "postage_flag": postage_flag, "point_rate": round(point_rate_equiv, 2),
                "review_avg": it.review_avg, "review_count": it.review_count,
                "query": keyword or f"jan:{jan}",
            })
            if prod:
                history_to_save.append({
                    "product_id": int(prod["id"]), "source": "Yahoo!",
                    "price": it.price, "sales_rank": "",
                })

    saved_ids: list[int] = []
    if save and rows_to_save:
        saved_ids = sheets.append_many("sourced_items", rows_to_save)
        if history_to_save:
            sheets.append_many("price_history", history_to_save)

    filtered = candidates
    if min_roi is not None:
        filtered = [(it, c, pid) for it, c, pid in candidates
                    if c.breakdown and c.roi * 100 >= min_roi]
    if not filtered:
        click.echo(f"(ROI {min_roi}% 以上の候補なし。全{len(candidates)}件)")
    else:
        rows = []
        for i, (it, c, _pid) in enumerate(filtered):
            rows.append({
                "#": i + 1, "shop": c.shop_name[:12], "title": c.title[:40],
                "JAN": it.jan or "-", "Yahoo!": f"{c.purchase_price:,}",
                "実質": f"{c.effective_cost:,}",
                "Amazon": f"{c.amazon_price:,}" if c.amazon_price else "未登録",
                "損益分岐": f"{c.breakeven_amazon:,}",
                "粗利": f"{c.profit:+,}" if c.breakdown else "-",
                "ROI%": f"{c.roi*100:.1f}" if c.breakdown else "-",
            })
        click.echo(tabulate(rows, headers="keys", tablefmt="github"))

    click.echo(f"\n取得 {len(items)} 件 / 保存 {len(saved_ids)} 件 / キーワード: {keyword or jan}")
    jan_count = sum(1 for it in items if it.jan)
    click.echo(f"JAN取得率: {jan_count}/{len(items)} 件 ({jan_count/len(items)*100:.0f}%)")


# ---------- 楽天/Yahoo横断の価格比較 ----------
@research.command("compare", help="JANコード指定で楽天×Yahoo!×Amazon価格を横並び比較")
@click.option("--jan", required=True, help="JANコード")
@click.option("--category", type=click.Choice(CATEGORIES), default="その他")
def compare(jan, category):
    provider = amazon_provider.get_provider()

    # Amazon価格(商品マスターに ASIN と JAN 両方あれば)
    prod = sheets.find_one("products", jan=jan)
    amazon_info = ""
    if prod and prod.get("asin"):
        ap = provider.get_price(prod["asin"])
        if ap:
            amazon_info = f"Amazon: {ap.price:,}円 (rank={ap.sales_rank or '-'})"

    # Yahoo!をJANで検索
    try:
        y_items = yahoo.search("", jan=jan, hits=10)
    except yahoo.YahooAPIError as e:
        click.echo(f"Yahoo!エラー: {e}")
        y_items = []

    # 楽天はJAN検索できないので、商品名ベースで検索
    r_items = []
    if prod and prod.get("name"):
        try:
            r_items = rakuten.search(prod["name"], hits=5)
        except rakuten.RakutenAPIError as e:
            click.echo(f"楽天エラー: {e}")

    if amazon_info:
        click.echo(amazon_info)
        click.echo()

    rows = []
    for it in y_items:
        effective = it.price - it.point_amount + (0 if it.shipping_free else 500)
        rows.append({"source": "Yahoo!", "shop": it.shop_name[:15],
                     "price": f"{it.price:,}", "実質": f"{effective:,}",
                     "review": f"{it.review_avg:.1f}({it.review_count})"})
    for it in r_items:
        point_back = int(it.price * it.point_rate / 100)
        shipping = 0 if it.postage_flag == 0 else 500
        effective = it.price - point_back + shipping
        rows.append({"source": "楽天", "shop": it.shop_name[:15],
                     "price": f"{it.price:,}", "実質": f"{effective:,}",
                     "review": f"{it.review_avg:.1f}({it.review_count})"})
    if not rows:
        click.echo(f"(JAN={jan} の商品が見つかりませんでした)")
        return
    # 実質価格で昇順ソート
    rows.sort(key=lambda r: int(r["実質"].replace(",", "")))
    click.echo(tabulate(rows, headers="keys", tablefmt="github"))


# ---------- sourced_items 操作 ----------
@research.command("list", help="取得済み候補を一覧")
@click.option("--source", default="楽天")
@click.option("--query", "q", default=None, help="取得時のクエリで絞り込み")
@click.option("--no-asin", is_flag=True, help="ASIN未紐づけのみ")
@click.option("--limit", default=30, type=int)
def list_sourced(source, q, no_asin, limit):
    rows = sheets.all_records("sourced_items")
    rows = [r for r in rows if r.get("source") == source]
    if q:
        rows = [r for r in rows if q in (r.get("query") or "")]
    if no_asin:
        rows = [r for r in rows if not r.get("asin")]
    rows.sort(key=lambda r: r.get("fetched_at", ""), reverse=True)
    rows = rows[:limit]
    if not rows:
        click.echo("(該当なし)")
        return
    out = [{
        "id": r["id"], "source": r["source"],
        "title": (r.get("title") or "")[:50],
        "price": f'{int(r["price"]):,}' if r.get("price") else "",
        "shop": (r.get("shop_name") or "")[:15],
        "asin": r.get("asin") or "-",
        "query": r.get("query"), "fetched": r.get("fetched_at"),
    } for r in rows]
    click.echo(tabulate(out, headers="keys", tablefmt="github"))


@research.command("link", help="sourced_item に ASIN と商品マスターを紐づけ")
@click.option("--sourced-id", required=True, type=int)
@click.option("--asin", required=True)
@click.option("--product-id", type=int, default=None,
              help="既存商品ID。省略時は ASIN で検索")
def link(sourced_id, asin, product_id):
    si = sheets.find_by_id("sourced_items", sourced_id)
    if not si:
        raise click.ClickException(f"sourced_id={sourced_id} が存在しません")

    if product_id is None:
        prod = sheets.find_one("products", asin=asin)
        if prod:
            product_id = int(prod["id"])
        else:
            raise click.ClickException(
                f"ASIN={asin} の商品がマスターに未登録です。\n"
                f"先に: python sedori.py product add --name \"{(si.get('title') or '')[:30]}\" --category <cat> --asin {asin}"
            )
    else:
        prod = sheets.find_by_id("products", product_id)
        if not prod:
            raise click.ClickException(f"product_id={product_id} が存在しません")
        if not prod.get("asin"):
            sheets.update_by_id("products", product_id, asin=asin)

    sheets.update_by_id("sourced_items", sourced_id, asin=asin, product_id=product_id)
    click.echo(f"紐づけ完了: sourced_id={sourced_id} → product_id={product_id} (ASIN={asin})")


# ---------- Amazon価格登録 ----------
@research.command("amazon-set", help="Amazon価格を手動登録(Keepa契約前の暫定)")
@click.option("--asin", required=True)
@click.option("--price", required=True, type=int)
@click.option("--rank", "sales_rank", type=int, default=None, help="Amazonランキング")
def amazon_set(asin, price, sales_rank):
    try:
        pid = amazon_provider.save_manual_price(asin, price, sales_rank)
    except ValueError as e:
        raise click.ClickException(str(e))
    click.echo(f"Amazon価格登録: product_id={pid} ASIN={asin} 価格={price:,}円 ランク={sales_rank}")


# ---------- 候補スコアリング ----------
@research.command("score", help="保存済み sourced_items を現在のAmazon価格で再スコアリング")
@click.option("--category", type=click.Choice(CATEGORIES), default="その他")
@click.option("--min-roi", type=float, default=20.0)
@click.option("--source", default="楽天")
def score(category, min_roi, source):
    provider = amazon_provider.get_provider()
    items = sheets.all_records("sourced_items")
    products_by_id = {int(p["id"]): p for p in sheets.all_records("products")}
    rows_out = []
    for r in items:
        if r.get("source") != source:
            continue
        asin = r.get("asin")
        cat = category
        if not asin and r.get("product_id"):
            p = products_by_id.get(int(r["product_id"]))
            if p:
                asin = p.get("asin")
                cat = p.get("category", category)
        if not asin:
            continue
        ap = provider.get_price(asin)
        if not ap:
            continue
        c = score_rakuten_item(
            title=r.get("title", ""), purchase_price=int(r["price"]),
            point_rate=float(r.get("point_rate") or 1),
            postage_flag=int(r.get("postage_flag") or 0),
            shop_name=r.get("shop_name", ""), url=r.get("url", ""),
            category=cat, amazon_price=ap.price, sales_rank=ap.sales_rank,
        )
        if c.roi * 100 >= min_roi:
            rows_out.append({
                "sid": r["id"], "asin": asin, "title": c.title[:40],
                "楽天": f"{c.purchase_price:,}", "Amazon": f"{c.amazon_price:,}",
                "粗利": f"{c.profit:+,}", "ROI%": f"{c.roi*100:.1f}",
                "rank": ap.sales_rank or "-",
            })
    if not rows_out:
        click.echo(f"(ROI {min_roi}% 以上かつASIN紐づけ済みの候補なし)")
        return
    click.echo(tabulate(sorted(rows_out, key=lambda x: float(x["ROI%"]), reverse=True),
                        headers="keys", tablefmt="github"))


# ---------- 価格履歴(トレンド) ----------
@research.command("trend", help="商品の価格履歴を表示")
@click.option("--product-id", type=int, default=None)
@click.option("--asin", default=None)
@click.option("--days", type=int, default=30)
def trend(product_id, asin, days):
    if not product_id and not asin:
        raise click.ClickException("--product-id か --asin のどちらかを指定してください")
    if asin and not product_id:
        prod = sheets.find_one("products", asin=asin)
        if not prod:
            raise click.ClickException(f"ASIN={asin} の商品が見つかりません")
        product_id = int(prod["id"])
    history = sheets.find_all("price_history", product_id=product_id)
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    history = [h for h in history if h.get("fetched_at", "") >= cutoff]
    history.sort(key=lambda h: h.get("fetched_at", ""))
    if not history:
        click.echo(f"(直近 {days} 日の履歴なし)")
        return
    out = [{"fetched_at": h.get("fetched_at"), "source": h.get("source"),
            "price": h.get("price"), "sales_rank": h.get("sales_rank")} for h in history]
    click.echo(tabulate(out, headers="keys", tablefmt="github"))
