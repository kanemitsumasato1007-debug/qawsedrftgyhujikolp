"""ダッシュボード: KPI指標、月次推移、販路別・カテゴリ別、在庫滞留、候補ランキング"""
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from shared import sheets
from app.style import apply_style, render_background_toggle

st.set_page_config(page_title="ダッシュボード", page_icon="🏠", layout="wide")
apply_style()
render_background_toggle()
st.markdown("""
<div class="sedori-hero" style="padding: 16px 0 24px 0;">
  <h1 class="sedori-hero-title" style="font-size: 2rem;">🏠 Dashboard</h1>
  <p class="sedori-hero-subtitle">売上・利益・在庫を俯瞰</p>
</div>
""", unsafe_allow_html=True)


# ====================================================================
# データ読み込み
# ====================================================================
@st.cache_data(ttl=60)
def load_data():
    products = sheets.all_records("products")
    purchases = sheets.all_records("purchases")
    sales = sheets.all_records("sales")
    sourced = sheets.all_records("sourced_items")
    return products, purchases, sales, sourced


def enriched_sales(sales, purchases, products):
    """sales を products/purchases と結合して粗利計算した行を返す。"""
    purchases_idx = {int(p["id"]): p for p in purchases if p.get("id")}
    products_idx = {int(pr["id"]): pr for pr in products if pr.get("id")}
    rows = []
    for s in sales:
        p = purchases_idx.get(int(s["purchase_id"])) if s.get("purchase_id") else None
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
        rows.append({
            "sale_id": s["id"], "date": s["sale_date"],
            "product": prod.get("name", ""), "category": prod.get("category", "未分類"),
            "channel": s["channel"],
            "sales": sale_total, "cost": cost, "fees": fees, "profit": profit,
            "quantity": qty,
        })
    return rows


if st.button("🔄 データ更新", help="Sheetsの最新内容を読み込み"):
    load_data.clear()

products, purchases, sales, sourced = load_data()
enriched = enriched_sales(sales, purchases, products)


# ====================================================================
# KPI 指標カード
# ====================================================================
st.subheader("📊 KPI (今月・今年・累計)")

today = datetime.now()
this_month = today.strftime("%Y-%m")
this_year = today.strftime("%Y")

this_month_sales = [r for r in enriched if (r["date"] or "").startswith(this_month)]
this_year_sales = [r for r in enriched if (r["date"] or "").startswith(this_year)]

def sum_of(rows, key):
    return sum(r[key] for r in rows)


col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("今月の売上", f"¥{sum_of(this_month_sales, 'sales'):,}",
              help=f"{len(this_month_sales)}件")
with col2:
    st.metric("今月の粗利", f"¥{sum_of(this_month_sales, 'profit'):,}")
with col3:
    st.metric("今年の粗利", f"¥{sum_of(this_year_sales, 'profit'):,}")
with col4:
    total_profit = sum_of(enriched, "profit")
    st.metric("累計粗利", f"¥{total_profit:,}", help=f"{len(enriched)}件")
with col5:
    # 未販売在庫
    sold_by_purchase = defaultdict(int)
    for s in sales:
        sold_by_purchase[int(s["purchase_id"])] += int(s["quantity"])
    remaining_total = 0
    remaining_cost = 0
    for p in purchases:
        if not p.get("id"):
            continue
        rem = int(p["quantity"]) - sold_by_purchase.get(int(p["id"]), 0)
        if rem > 0:
            remaining_total += rem
            remaining_cost += int(p["unit_price"]) * rem
    st.metric("未販売在庫", f"{remaining_total} 点",
              delta=f"¥{remaining_cost:,} の資産" if remaining_cost > 0 else None,
              delta_color="off")

st.divider()


# ====================================================================
# 月次推移 (折れ線グラフ)
# ====================================================================
st.subheader("📈 月次推移")

if not enriched:
    st.info("販売記録がまだありません。「💰 記録入力」画面から追加してください。")
else:
    monthly = defaultdict(lambda: {"sales": 0, "profit": 0, "cnt": 0})
    for r in enriched:
        m = (r["date"] or "")[:7]
        if not m:
            continue
        monthly[m]["sales"] += r["sales"]
        monthly[m]["profit"] += r["profit"]
        monthly[m]["cnt"] += 1

    df_monthly = pd.DataFrame([
        {"month": m, "売上": v["sales"], "粗利": v["profit"], "件数": v["cnt"]}
        for m, v in sorted(monthly.items())
    ])

    tab_line, tab_bar = st.tabs(["折れ線", "棒グラフ"])
    with tab_line:
        fig = px.line(df_monthly, x="month", y=["売上", "粗利"],
                      markers=True, title="月次 売上・粗利推移")
        fig.update_layout(yaxis_tickformat=",", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    with tab_bar:
        fig2 = px.bar(df_monthly, x="month", y="粗利", text_auto=True,
                      color="粗利", color_continuous_scale="Blues",
                      title="月次粗利")
        fig2.update_layout(yaxis_tickformat=",")
        st.plotly_chart(fig2, use_container_width=True)


# ====================================================================
# 販路別 × カテゴリ別 (並置)
# ====================================================================
if enriched:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🛒 販路別")
        by_channel = defaultdict(lambda: {"sales": 0, "profit": 0, "cnt": 0})
        for r in enriched:
            a = by_channel[r["channel"]]
            a["sales"] += r["sales"]; a["profit"] += r["profit"]; a["cnt"] += 1
        df_ch = pd.DataFrame([{"販路": c, **v} for c, v in by_channel.items()])
        fig = px.pie(df_ch, names="販路", values="profit", title="販路別 粗利シェア", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_ch.sort_values("profit", ascending=False),
                     hide_index=True, use_container_width=True,
                     column_config={
                         "sales": st.column_config.NumberColumn(format="¥%d"),
                         "profit": st.column_config.NumberColumn(format="¥%+d"),
                     })

    with c2:
        st.subheader("🏷️ カテゴリ別")
        by_cat = defaultdict(lambda: {"sales": 0, "profit": 0, "cnt": 0})
        for r in enriched:
            a = by_cat[r["category"]]
            a["sales"] += r["sales"]; a["profit"] += r["profit"]; a["cnt"] += 1
        df_cat = pd.DataFrame([{"カテゴリ": c, **v} for c, v in by_cat.items()])
        fig = px.bar(df_cat.sort_values("profit", ascending=True),
                     y="カテゴリ", x="profit", orientation="h",
                     color="profit", color_continuous_scale="Greens",
                     title="カテゴリ別 粗利")
        fig.update_layout(xaxis_tickformat=",")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_cat.sort_values("profit", ascending=False),
                     hide_index=True, use_container_width=True,
                     column_config={
                         "sales": st.column_config.NumberColumn(format="¥%d"),
                         "profit": st.column_config.NumberColumn(format="¥%+d"),
                     })


st.divider()


# ====================================================================
# 在庫滞留ランキング
# ====================================================================
st.subheader("📦 在庫滞留ランキング (長い順)")

products_idx = {int(pr["id"]): pr for pr in products if pr.get("id")}
inventory_rows = []
today_d = today.date()
for p in purchases:
    if not p.get("id"):
        continue
    rem = int(p["quantity"]) - sold_by_purchase.get(int(p["id"]), 0)
    if rem <= 0:
        continue
    try:
        d = datetime.strptime(p["purchase_date"], "%Y-%m-%d").date()
        days = (today_d - d).days
    except Exception:
        days = 0
    prod = products_idx.get(int(p["product_id"]), {})
    inventory_rows.append({
        "product": prod.get("name", ""), "category": prod.get("category", ""),
        "source": p["source"], "unit_price": int(p["unit_price"]),
        "remaining": rem, "days_held": days,
        "拘束資金": int(p["unit_price"]) * rem,
    })

if not inventory_rows:
    st.success("在庫なし(すべて販売済み)")
else:
    df_inv = pd.DataFrame(inventory_rows).sort_values("days_held", ascending=False).head(15)
    st.dataframe(
        df_inv, hide_index=True, use_container_width=True,
        column_config={
            "unit_price": st.column_config.NumberColumn(format="¥%d"),
            "拘束資金": st.column_config.NumberColumn(format="¥%d"),
            "days_held": st.column_config.ProgressColumn("保有日数", min_value=0, max_value=90,
                                                         format="%d 日"),
        },
    )


st.divider()


# ====================================================================
# リサーチ候補ランキング
# ====================================================================
st.subheader("🔍 リサーチ候補 (新着順 Top 20)")

if not sourced:
    st.info("候補データがありません。「🔍 リサーチ」画面で楽天/Yahoo!検索してください。")
else:
    df_s = pd.DataFrame(sourced)
    if "fetched_at" in df_s.columns:
        df_s = df_s.sort_values("fetched_at", ascending=False)
    display = df_s[["source", "title", "price", "shop_name", "jan", "asin", "query", "url"]].head(20)
    st.dataframe(
        display, hide_index=True, use_container_width=True,
        column_config={
            "url": st.column_config.LinkColumn("URL", display_text="🔗"),
            "price": st.column_config.NumberColumn(format="¥%d"),
            "title": st.column_config.TextColumn(width="large"),
        },
    )


st.caption(f"データ更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
