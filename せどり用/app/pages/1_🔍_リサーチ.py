"""リサーチ画面: 楽天/Yahoo!検索、既存候補一覧、ASIN紐づけ、Amazon価格登録"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd

from shared import sheets
from shared.config import CATEGORIES
from research import rakuten, yahoo, amazon_provider
from research.scorer import score_rakuten_item
from app.style import apply_style, render_background_toggle

st.set_page_config(page_title="リサーチ", page_icon="🔍", layout="wide")
apply_style()
render_background_toggle()
st.markdown("""
<div class="sedori-hero" style="padding: 16px 0 24px 0;">
  <h1 class="sedori-hero-title" style="font-size: 2rem;">🔍 Research</h1>
  <p class="sedori-hero-subtitle">楽天 · Yahoo! · Amazon を横断してリサーチ</p>
</div>
""", unsafe_allow_html=True)

# ====================================================================
# タブ構成
# ====================================================================
tab_search, tab_list, tab_link, tab_compare = st.tabs([
    "🔎 新規検索", "📋 候補一覧", "🔗 ASIN紐づけ / Amazon価格", "⚖️ 販路横断比較"
])


# ====================================================================
# タブ1: 新規検索
# ====================================================================
with tab_search:
    st.subheader("楽天 / Yahoo! を検索")

    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    with c1:
        keyword = st.text_input("キーワード", value="", placeholder="例: ノースフェイス ジャケット")
    with c2:
        source = st.selectbox("検索先", ["Yahoo!", "楽天", "両方"])
    with c3:
        category = st.selectbox("カテゴリ", CATEGORIES, index=CATEGORIES.index("その他"))
    with c4:
        pages = st.number_input("ページ数", min_value=1, max_value=5, value=1)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        min_price = st.number_input("最低価格", min_value=0, value=0, step=500)
    with c6:
        max_price = st.number_input("最高価格", min_value=0, value=0, step=500,
                                    help="0で無制限")
    with c7:
        include_random = st.checkbox("福袋/ガチャ等を含める", value=False)
    with c8:
        save = st.checkbox("Sheetsに保存", value=True)

    if st.button("🔎 検索実行", type="primary", disabled=not keyword):
        with st.spinner("検索中..."):
            min_p = min_price if min_price > 0 else None
            max_p = max_price if max_price > 0 else None
            all_results = []

            try:
                if source in ("Yahoo!", "両方"):
                    y_items = yahoo.search(
                        keyword, min_price=min_p, max_price=max_p,
                        max_pages=int(pages), exclude_random=not include_random,
                    )
                    for it in y_items:
                        all_results.append({
                            "source": "Yahoo!", "title": it.title,
                            "price": it.price, "shop": it.shop_name,
                            "jan": it.jan or "", "url": it.url,
                            "point": it.point_amount,
                            "shipping_free": it.shipping_free,
                            "review_avg": it.review_avg,
                            "review_count": it.review_count,
                            "item_code": it.item_code,
                            "image_url": it.image_url,
                            "postage_flag": 0 if it.shipping_free else 1,
                            "point_rate": max(1.0, it.point_amount / it.price * 100) if it.price else 1,
                        })
            except yahoo.YahooAPIError as e:
                st.error(f"Yahoo!エラー: {e}")

            try:
                if source in ("楽天", "両方"):
                    r_items = rakuten.search(
                        keyword, min_price=min_p, max_price=max_p,
                        max_pages=int(pages), exclude_random=not include_random,
                    )
                    for it in r_items:
                        all_results.append({
                            "source": "楽天", "title": it.title,
                            "price": it.price, "shop": it.shop_name,
                            "jan": "", "url": it.url,
                            "point": int(it.price * it.point_rate / 100),
                            "shipping_free": (it.postage_flag == 0),
                            "review_avg": it.review_avg,
                            "review_count": it.review_count,
                            "item_code": it.item_code,
                            "image_url": it.image_url,
                            "postage_flag": it.postage_flag,
                            "point_rate": it.point_rate,
                        })
            except rakuten.RakutenAPIError as e:
                st.error(f"楽天エラー: {e}")

        if not all_results:
            st.warning("ヒットなし")
        else:
            provider = amazon_provider.get_provider()
            products = sheets.all_records("products")
            jan_to_product = {p.get("jan"): p for p in products if p.get("jan")}

            # スコアリング
            scored_rows = []
            for r in all_results:
                prod = jan_to_product.get(r["jan"]) if r["jan"] else None
                amazon_price = None
                if prod and prod.get("asin"):
                    ap = provider.get_price(prod["asin"])
                    if ap:
                        amazon_price = ap.price

                cand = score_rakuten_item(
                    title=r["title"], purchase_price=r["price"],
                    point_rate=r["point_rate"], postage_flag=r["postage_flag"],
                    shop_name=r["shop"], url=r["url"], category=category,
                    amazon_price=amazon_price,
                    source_label=r["source"],
                )
                scored_rows.append({
                    "source": r["source"],
                    "shop": r["shop"][:20],
                    "title": r["title"][:60],
                    "JAN": r["jan"] or "-",
                    "価格": r["price"],
                    "実質": cand.effective_cost,
                    "Amazon": amazon_price or 0,
                    "損益分岐": cand.breakeven_amazon,
                    "粗利": cand.profit if cand.breakdown else None,
                    "ROI%": round(cand.roi * 100, 1) if cand.breakdown else None,
                    "review": f"{r['review_avg']:.1f}({r['review_count']})",
                    "URL": r["url"],
                })

            df = pd.DataFrame(scored_rows)
            df = df.sort_values(by="ROI%", ascending=False, na_position="last")

            st.success(f"{len(scored_rows)} 件取得")

            # ROIでハイライト
            def highlight_roi(val):
                try:
                    v = float(val)
                    if v >= 30:
                        return "background-color: #c8e6c9"
                    if v >= 15:
                        return "background-color: #fff9c4"
                    if v < 0:
                        return "background-color: #ffcdd2"
                except Exception:
                    pass
                return ""

            styled = df.style.map(highlight_roi, subset=["ROI%"])
            st.dataframe(
                styled,
                column_config={
                    "URL": st.column_config.LinkColumn("URL", display_text="開く"),
                    "価格": st.column_config.NumberColumn(format="¥%d"),
                    "実質": st.column_config.NumberColumn(format="¥%d"),
                    "Amazon": st.column_config.NumberColumn(format="¥%d"),
                    "損益分岐": st.column_config.NumberColumn(format="¥%d"),
                    "粗利": st.column_config.NumberColumn(format="¥%+d"),
                },
                use_container_width=True, hide_index=True, height=500,
            )

            # Sheetsに保存
            if save:
                with st.spinner("Sheetsに保存中..."):
                    rows_to_save = []
                    history_to_save = []
                    for r in all_results:
                        prod = jan_to_product.get(r["jan"]) if r["jan"] else None
                        rows_to_save.append({
                            "source": r["source"], "source_item_id": r["item_code"],
                            "product_id": int(prod["id"]) if prod else "",
                            "asin": (prod or {}).get("asin", ""),
                            "jan": r["jan"] or "",
                            "title": r["title"], "price": r["price"],
                            "shop_name": r["shop"], "url": r["url"],
                            "image_url": r["image_url"],
                            "postage_flag": r["postage_flag"],
                            "point_rate": round(r["point_rate"], 2),
                            "review_avg": r["review_avg"],
                            "review_count": r["review_count"],
                            "query": keyword,
                        })
                        if prod:
                            history_to_save.append({
                                "product_id": int(prod["id"]), "source": r["source"],
                                "price": r["price"], "sales_rank": "",
                            })
                    sheets.append_many("sourced_items", rows_to_save)
                    if history_to_save:
                        sheets.append_many("price_history", history_to_save)
                st.toast(f"✅ {len(rows_to_save)}件をSheetsに保存しました")


# ====================================================================
# タブ2: 候補一覧
# ====================================================================
with tab_list:
    st.subheader("保存済みの候補")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        query_filter = st.text_input("クエリ絞り込み", placeholder="例: ノースフェイス")
    with c2:
        source_filter = st.multiselect("販路", ["楽天", "Yahoo!"], default=["楽天", "Yahoo!"])
    with c3:
        show_linked = st.radio("ASIN状態", ["全て", "未紐づけのみ", "紐づけ済のみ"], horizontal=False)

    rows = sheets.all_records("sourced_items")
    if source_filter:
        rows = [r for r in rows if r.get("source") in source_filter]
    if query_filter:
        rows = [r for r in rows if query_filter in (r.get("query") or "")]
    if show_linked == "未紐づけのみ":
        rows = [r for r in rows if not r.get("asin")]
    elif show_linked == "紐づけ済のみ":
        rows = [r for r in rows if r.get("asin")]

    if not rows:
        st.info("(該当なし)")
    else:
        df = pd.DataFrame(rows)
        # 新しい順
        df = df.sort_values(by="fetched_at", ascending=False) if "fetched_at" in df.columns else df
        display_cols = [c for c in ["id", "source", "title", "price", "shop_name", "jan", "asin", "url", "query", "fetched_at"] if c in df.columns]
        st.dataframe(
            df[display_cols],
            column_config={
                "url": st.column_config.LinkColumn("URL", display_text="開く"),
                "price": st.column_config.NumberColumn(format="¥%d"),
            },
            use_container_width=True, hide_index=True, height=500,
        )
        st.caption(f"{len(rows)} 件表示")


# ====================================================================
# タブ3: ASIN紐づけ / Amazon価格登録
# ====================================================================
with tab_link:
    st.subheader("商品マスター登録・ASIN紐づけ・Amazon価格登録")

    st.markdown("#### ① 商品マスターに登録")
    with st.form("product_add_form"):
        c1, c2 = st.columns(2)
        with c1:
            p_name = st.text_input("商品名*")
            p_category = st.selectbox("カテゴリ*", CATEGORIES)
            p_asin = st.text_input("ASIN (B0で始まる10文字)")
        with c2:
            p_jan = st.text_input("JANコード")
            p_sku = st.text_input("管理SKU", placeholder="任意")
            p_memo = st.text_area("メモ", placeholder="任意")
        submitted = st.form_submit_button("商品登録", type="primary")
        if submitted:
            if not p_name or not p_category:
                st.error("商品名とカテゴリは必須")
            else:
                new_id = sheets.append("products", {
                    "name": p_name, "category": p_category,
                    "jan": p_jan, "asin": p_asin, "sku": p_sku, "memo": p_memo,
                })
                st.success(f"商品登録完了: id={new_id}")

    st.divider()

    st.markdown("#### ② sourced_item と商品マスター/ASINを紐づけ")
    with st.form("link_form"):
        c1, c2 = st.columns(2)
        with c1:
            link_sid = st.number_input("sourced_id (候補一覧タブで確認)", min_value=1, value=1)
        with c2:
            link_asin = st.text_input("紐づけるASIN")
        link_btn = st.form_submit_button("紐づけ実行")
        if link_btn:
            si = sheets.find_by_id("sourced_items", link_sid)
            if not si:
                st.error(f"sourced_id={link_sid} が存在しません")
            elif not link_asin:
                st.error("ASINを入力してください")
            else:
                prod = sheets.find_one("products", asin=link_asin)
                if not prod:
                    st.error(f"ASIN={link_asin} の商品がマスターに未登録。先に①で登録してください。")
                else:
                    sheets.update_by_id("sourced_items", link_sid,
                                        asin=link_asin, product_id=int(prod["id"]))
                    st.success(f"紐づけ完了: sourced_id={link_sid} → product_id={prod['id']}")

    st.divider()

    st.markdown("#### ③ Amazon価格を手動登録 (Keepa契約前の暫定)")
    with st.form("amazon_price_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            amz_asin = st.text_input("ASIN*")
        with c2:
            amz_price = st.number_input("現在価格(円)*", min_value=0, value=0, step=100)
        with c3:
            amz_rank = st.number_input("Amazonランキング(任意)", min_value=0, value=0)
        amz_btn = st.form_submit_button("Amazon価格登録", type="primary")
        if amz_btn:
            if not amz_asin or amz_price <= 0:
                st.error("ASINと価格は必須")
            else:
                try:
                    pid = amazon_provider.save_manual_price(
                        amz_asin, int(amz_price),
                        int(amz_rank) if amz_rank > 0 else None,
                    )
                    st.success(f"登録完了: product_id={pid} ASIN={amz_asin} 価格=¥{amz_price:,}")
                except ValueError as e:
                    st.error(str(e))


# ====================================================================
# タブ4: 販路横断比較
# ====================================================================
with tab_compare:
    st.subheader("JANコードで楽天 × Yahoo! × Amazon を横並び比較")

    c1, c2 = st.columns([2, 1])
    with c1:
        compare_jan = st.text_input("JANコード", placeholder="例: 4580777900131")
    with c2:
        compare_cat = st.selectbox("カテゴリ", CATEGORIES, key="cmp_cat",
                                    index=CATEGORIES.index("アパレル"))

    if st.button("比較実行", type="primary", disabled=not compare_jan):
        provider = amazon_provider.get_provider()
        prod = sheets.find_one("products", jan=compare_jan)

        col_amz, col_mkt = st.columns([1, 2])

        with col_amz:
            st.markdown("#### Amazon")
            if prod and prod.get("asin"):
                ap = provider.get_price(prod["asin"])
                if ap:
                    st.metric("Amazon価格", f"¥{ap.price:,}",
                              help=f"ASIN: {prod['asin']} / ランク: {ap.sales_rank or '-'}")
                else:
                    st.info("Amazon価格未登録")
            else:
                st.info("商品マスター未登録 or ASIN未紐づけ")

        with col_mkt:
            rows = []
            try:
                for it in yahoo.search("", jan=compare_jan, hits=20):
                    effective = it.price - it.point_amount + (0 if it.shipping_free else 500)
                    rows.append({
                        "source": "Yahoo!", "shop": it.shop_name[:20],
                        "price": it.price, "実質": effective,
                        "review": f"{it.review_avg:.1f}({it.review_count})",
                        "url": it.url,
                    })
            except yahoo.YahooAPIError as e:
                st.warning(f"Yahoo!エラー: {e}")

            if prod and prod.get("name"):
                try:
                    for it in rakuten.search(prod["name"], hits=10):
                        pb = int(it.price * it.point_rate / 100)
                        ship = 0 if it.postage_flag == 0 else 500
                        effective = it.price - pb + ship
                        rows.append({
                            "source": "楽天", "shop": it.shop_name[:20],
                            "price": it.price, "実質": effective,
                            "review": f"{it.review_avg:.1f}({it.review_count})",
                            "url": it.url,
                        })
                except rakuten.RakutenAPIError as e:
                    st.warning(f"楽天エラー: {e}")

            if not rows:
                st.info("(データなし)")
            else:
                df = pd.DataFrame(rows).sort_values(by="実質")
                st.dataframe(
                    df,
                    column_config={
                        "url": st.column_config.LinkColumn("開く", display_text="🔗"),
                        "price": st.column_config.NumberColumn(format="¥%d"),
                        "実質": st.column_config.NumberColumn(format="¥%d"),
                    },
                    use_container_width=True, hide_index=True, height=400,
                )
                cheapest = df.iloc[0]
                st.success(f"🏆 最安: {cheapest['source']} / {cheapest['shop']} / 実質 ¥{int(cheapest['実質']):,}")
