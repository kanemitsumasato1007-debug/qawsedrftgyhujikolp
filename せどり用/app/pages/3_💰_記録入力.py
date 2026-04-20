"""記録入力: 商品マスター・仕入・販売のフォーム入力、履歴閲覧"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from shared import sheets
from shared.config import CATEGORIES, PURCHASE_SOURCES, SALE_CHANNELS
from shared.fees import platform_fee, calc_profit
from app.style import apply_style, render_background_toggle

st.set_page_config(page_title="記録入力", page_icon="💰", layout="wide")
apply_style()
render_background_toggle()
st.markdown("""
<div class="sedori-hero" style="padding: 16px 0 24px 0;">
  <h1 class="sedori-hero-title" style="font-size: 2rem;">💰 Records</h1>
  <p class="sedori-hero-subtitle">仕入 · 販売 · 商品マスターを記録</p>
</div>
""", unsafe_allow_html=True)


tab_purchase, tab_sale, tab_products, tab_history = st.tabs([
    "🛒 仕入記録", "💴 販売記録", "📦 商品マスター", "📜 履歴閲覧"
])


# ====================================================================
# タブ1: 仕入記録入力
# ====================================================================
with tab_purchase:
    st.subheader("仕入れを記録")

    products = sheets.all_records("products")
    if not products:
        st.warning("商品マスターが空です。先に「📦 商品マスター」タブで商品を登録してください。")
    else:
        # 商品選択肢(id付きラベル)
        product_options = {
            f"[{p['id']}] {p['name']} ({p['category']})": int(p["id"])
            for p in products
        }

        with st.form("purchase_form"):
            c1, c2 = st.columns([2, 1])
            with c1:
                product_label = st.selectbox(
                    "商品*", list(product_options.keys()),
                    help="商品マスター未登録なら先に登録してください"
                )
            with c2:
                purchase_date = st.date_input("仕入日*", value=date.today())

            c3, c4, c5 = st.columns(3)
            with c3:
                source = st.selectbox("仕入先*", PURCHASE_SOURCES)
            with c4:
                store_name = st.text_input("店舗名/出品者名", placeholder="例: 楽天ブックス")
            with c5:
                pass

            c6, c7, c8, c9 = st.columns(4)
            with c6:
                unit_price = st.number_input("税込単価(円)*", min_value=1, value=1000, step=100)
            with c7:
                quantity = st.number_input("数量*", min_value=1, value=1, step=1)
            with c8:
                shipping_in = st.number_input("仕入送料(円)", min_value=0, value=0, step=100)
            with c9:
                point_back = st.number_input("ポイント還元(円相当)", min_value=0, value=0, step=10)

            memo = st.text_area("メモ", placeholder="任意")

            # プレビュー
            total_cost = unit_price * quantity + shipping_in - point_back
            st.info(f"**仕入原価合計: ¥{total_cost:,}** (単価×数量 + 送料 − ポイント還元)")

            submitted = st.form_submit_button("💾 仕入を登録", type="primary")
            if submitted:
                product_id = product_options[product_label]
                new_id = sheets.append("purchases", {
                    "product_id": product_id,
                    "purchase_date": purchase_date.strftime("%Y-%m-%d"),
                    "source": source, "store_name": store_name,
                    "unit_price": int(unit_price), "quantity": int(quantity),
                    "shipping_in": int(shipping_in), "point_back": int(point_back),
                    "memo": memo,
                })
                st.success(f"仕入登録完了: id={new_id}")
                st.toast(f"✅ 仕入原価合計 ¥{total_cost:,} を記録")


# ====================================================================
# タブ2: 販売記録入力
# ====================================================================
with tab_sale:
    st.subheader("販売を記録")

    purchases = sheets.all_records("purchases")
    sales_all = sheets.all_records("sales")
    products_idx = {int(p["id"]): p for p in sheets.all_records("products")}

    # 未販売残数ある仕入のみリスト化
    sold_by_p = {}
    for s in sales_all:
        pid = int(s["purchase_id"])
        sold_by_p[pid] = sold_by_p.get(pid, 0) + int(s["quantity"])

    available_purchases = []
    for p in purchases:
        if not p.get("id"):
            continue
        pid = int(p["id"])
        rem = int(p["quantity"]) - sold_by_p.get(pid, 0)
        if rem > 0:
            prod = products_idx.get(int(p["product_id"]), {})
            available_purchases.append({
                "label": f"[{pid}] {prod.get('name', '')[:30]} 残{rem}/{p['quantity']} @¥{int(p['unit_price']):,}",
                "id": pid, "remaining": rem, "purchase": p, "product": prod,
            })

    if not available_purchases:
        st.info("販売可能な仕入が見つかりません。先に仕入記録を入力してください。")
    else:
        purchase_labels = {ap["label"]: ap for ap in available_purchases}

        # st.form を使わず通常のウィジェットで即時プレビュー対応
        sel_label = st.selectbox("仕入*", list(purchase_labels.keys()))
        selected = purchase_labels[sel_label]
        max_qty = selected["remaining"]
        prod = selected["product"]
        category = prod.get("category", "その他")

        c1, c2, c3 = st.columns(3)
        with c1:
            sale_date = st.date_input("販売日*", value=date.today())
        with c2:
            channel = st.selectbox("販売先*", SALE_CHANNELS,
                                   index=SALE_CHANNELS.index("Amazon FBA"))
        with c3:
            quantity = st.number_input(f"数量* (残{max_qty})", min_value=1, max_value=max_qty, value=1)

        c4, c5 = st.columns(2)
        with c4:
            sale_price = st.number_input("販売価格(税込, 1点あたり)*",
                                          min_value=1, value=3000, step=100)
        with c5:
            auto_fee = st.checkbox("販売手数料を自動計算", value=True,
                                   help=f"カテゴリ「{category}」の料率で計算")

        c6, c7, c8 = st.columns(3)
        with c6:
            fba_fee = st.number_input("FBA手数料(1点)", min_value=0, value=0, step=50)
        with c7:
            shipping_out = st.number_input("出荷送料(1点)", min_value=0, value=0, step=50)
        with c8:
            other_cost = st.number_input("その他経費(1点)", min_value=0, value=0, step=50)

        if not auto_fee:
            manual_pf = st.number_input("販売手数料(円, 合計)", min_value=0, value=0, step=10)
        else:
            manual_pf = None

        memo = st.text_area("メモ", placeholder="任意", key="sale_memo")

        # 利益計算プレビュー(リアルタイム反映)
        computed_pf = (platform_fee(channel, int(sale_price), category) * int(quantity)
                       if auto_fee else int(manual_pf or 0))
        p = selected["purchase"]
        prorate_ship = round(int(p.get("shipping_in") or 0) * quantity / int(p["quantity"]))
        prorate_point = round(int(p.get("point_back") or 0) * quantity / int(p["quantity"]))
        breakdown = calc_profit(
            sale_price=int(sale_price), quantity=int(quantity),
            unit_purchase_price=int(p["unit_price"]),
            channel=channel, category=category,
            fba_fee=int(fba_fee), shipping_out=int(shipping_out),
            shipping_in=prorate_ship, point_back=prorate_point,
            other_cost=int(other_cost),
            override_platform_fee=computed_pf,
        )

        cm1, cm2, cm3 = st.columns(3)
        with cm1:
            st.metric("予想粗利", f"¥{breakdown.profit:+,}")
        with cm2:
            st.metric("ROI", f"{breakdown.roi * 100:.1f}%")
        with cm3:
            st.metric("利益率", f"{breakdown.margin * 100:.1f}%")

        with st.expander("内訳詳細"):
            st.text(breakdown.pretty())

        if st.button("💾 販売を登録", type="primary", key="sale_submit"):
            new_id = sheets.append("sales", {
                "purchase_id": selected["id"],
                "sale_date": sale_date.strftime("%Y-%m-%d"),
                "channel": channel,
                "sale_price": int(sale_price),
                "quantity": int(quantity),
                "platform_fee": computed_pf,
                "fba_fee": int(fba_fee) * int(quantity),
                "shipping_out": int(shipping_out) * int(quantity),
                "other_cost": int(other_cost) * int(quantity),
                "memo": memo,
            })
            st.success(f"販売登録完了: id={new_id} / 粗利 ¥{breakdown.profit:+,}")
            st.toast(f"✅ 販売記録 id={new_id}")


# ====================================================================
# タブ3: 商品マスター
# ====================================================================
with tab_products:
    st.subheader("商品マスター")

    sub_add, sub_list = st.tabs(["➕ 新規登録", "📋 一覧・編集"])

    with sub_add:
        with st.form("product_master_form"):
            c1, c2 = st.columns(2)
            with c1:
                p_name = st.text_input("商品名*")
                p_category = st.selectbox("カテゴリ*", CATEGORIES)
                p_asin = st.text_input("ASIN", help="Amazonの10桁コード(B0...)")
                p_jan = st.text_input("JANコード", help="13桁のバーコード")
            with c2:
                p_sku = st.text_input("管理SKU", placeholder="任意")
                p_url_amazon = st.text_input("Amazon URL", placeholder="任意")
                p_url_rakuten = st.text_input("楽天 URL", placeholder="任意")
                p_memo = st.text_area("メモ", placeholder="任意")

            submitted = st.form_submit_button("💾 商品を登録", type="primary")
            if submitted:
                if not p_name:
                    st.error("商品名は必須")
                else:
                    new_id = sheets.append("products", {
                        "name": p_name, "category": p_category,
                        "jan": p_jan, "asin": p_asin, "sku": p_sku,
                        "url_amazon": p_url_amazon, "url_rakuten": p_url_rakuten,
                        "memo": p_memo,
                    })
                    st.success(f"商品登録完了: id={new_id}")

    with sub_list:
        products = sheets.all_records("products")
        if not products:
            st.info("(登録なし)")
        else:
            c1, c2 = st.columns([2, 1])
            with c1:
                q = st.text_input("名前で絞り込み", key="prod_q")
            with c2:
                cat_filter = st.multiselect("カテゴリで絞り込み", CATEGORIES, default=list(CATEGORIES))

            filtered = [p for p in products if p.get("category") in cat_filter]
            if q:
                filtered = [p for p in filtered if q in (p.get("name") or "")]

            if filtered:
                df = pd.DataFrame(filtered)
                display_cols = [c for c in ["id", "name", "category", "jan", "asin", "sku",
                                             "url_amazon", "memo", "created_at"] if c in df.columns]
                st.dataframe(
                    df[display_cols],
                    column_config={
                        "url_amazon": st.column_config.LinkColumn("Amazon", display_text="🔗"),
                    },
                    hide_index=True, use_container_width=True,
                )
                st.caption(f"{len(filtered)} 件")
            else:
                st.info("(該当なし)")


# ====================================================================
# タブ4: 履歴閲覧
# ====================================================================
with tab_history:
    st.subheader("記録履歴")

    history_type = st.radio("表示するデータ", ["販売記録", "仕入記録"], horizontal=True)

    if history_type == "仕入記録":
        purchases = sheets.all_records("purchases")
        sales = sheets.all_records("sales")
        products_idx = {int(p["id"]): p for p in sheets.all_records("products")}
        sold_by_p = {}
        for s in sales:
            pid = int(s["purchase_id"])
            sold_by_p[pid] = sold_by_p.get(pid, 0) + int(s["quantity"])

        rows = []
        for p in purchases:
            if not p.get("id"):
                continue
            sold = sold_by_p.get(int(p["id"]), 0)
            rem = int(p["quantity"]) - sold
            prod = products_idx.get(int(p["product_id"]), {})
            rows.append({
                "id": p["id"], "date": p["purchase_date"],
                "product": prod.get("name", ""), "source": p["source"],
                "store": p.get("store_name", ""),
                "unit_price": int(p["unit_price"]),
                "quantity": int(p["quantity"]),
                "sold": sold, "remaining": rem,
                "shipping_in": int(p.get("shipping_in") or 0),
                "point_back": int(p.get("point_back") or 0),
                "memo": p.get("memo", ""),
            })

        if rows:
            df = pd.DataFrame(rows).sort_values(by=["date", "id"], ascending=False)
            st.dataframe(
                df, hide_index=True, use_container_width=True,
                column_config={
                    "unit_price": st.column_config.NumberColumn(format="¥%d"),
                    "shipping_in": st.column_config.NumberColumn(format="¥%d"),
                    "point_back": st.column_config.NumberColumn(format="¥%d"),
                },
            )
            st.caption(f"{len(rows)} 件")
        else:
            st.info("(仕入記録なし)")

    else:  # 販売記録
        sales = sheets.all_records("sales")
        purchases_idx = {int(p["id"]): p for p in sheets.all_records("purchases")}
        products_idx = {int(pr["id"]): pr for pr in sheets.all_records("products")}

        rows = []
        for s in sales:
            if not s.get("id"):
                continue
            p = purchases_idx.get(int(s["purchase_id"]), {})
            prod = products_idx.get(int(p.get("product_id") or 0), {})
            sale_total = int(s["sale_price"]) * int(s["quantity"])
            fees = (int(s.get("platform_fee") or 0) + int(s.get("fba_fee") or 0)
                    + int(s.get("shipping_out") or 0) + int(s.get("other_cost") or 0))
            rows.append({
                "id": s["id"], "date": s["sale_date"],
                "product": prod.get("name", ""), "channel": s["channel"],
                "sale_price": int(s["sale_price"]),
                "quantity": int(s["quantity"]),
                "売上合計": sale_total,
                "手数料合計": fees,
                "memo": s.get("memo", ""),
            })

        if rows:
            df = pd.DataFrame(rows).sort_values(by=["date", "id"], ascending=False)
            st.dataframe(
                df, hide_index=True, use_container_width=True,
                column_config={
                    "sale_price": st.column_config.NumberColumn(format="¥%d"),
                    "売上合計": st.column_config.NumberColumn(format="¥%d"),
                    "手数料合計": st.column_config.NumberColumn(format="¥%d"),
                },
            )
            st.caption(f"{len(rows)} 件")
        else:
            st.info("(販売記録なし)")
