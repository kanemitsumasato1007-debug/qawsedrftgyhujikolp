"""せどり管理ツール - ホーム画面(ミニマル・ヒーロー・カード型)"""
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.style import apply_style, render_background_toggle, _resolved_bg_override
from app.background import get_background_info

st.set_page_config(
    page_title="せどり管理",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "せどり管理ツール — Google Sheets と連携した副業せどり支援ツール",
    },
)
apply_style()

# カードクリックからのページ遷移
_NAV_TARGETS = {
    "research": "pages/1_🔍_リサーチ.py",
    "records": "pages/3_💰_記録入力.py",
    "dashboard": "pages/2_🏠_ダッシュボード.py",
}
_goto = st.query_params.get("goto")
if _goto in _NAV_TARGETS:
    target = _NAV_TARGETS[_goto]
    st.query_params.clear()
    st.switch_page(target)


# ====================================================================
# データ読み込み
# ====================================================================
@st.cache_data(ttl=60)
def load_overview():
    from shared import sheets
    products = sheets.all_records("products")
    purchases = sheets.all_records("purchases")
    sales = sheets.all_records("sales")
    sourced = sheets.all_records("sourced_items")
    sh = sheets._spreadsheet()
    return {
        "products": products, "purchases": purchases, "sales": sales,
        "sourced": sourced, "sheet_title": sh.title, "sheet_url": sh.url,
    }


try:
    data = load_overview()
    connected = True
    error = None
except Exception as e:
    connected = False
    error = str(e)
    data = {"products": [], "purchases": [], "sales": [], "sourced": [],
            "sheet_title": "(未接続)", "sheet_url": ""}


# ====================================================================
# Hero
# ====================================================================
today = datetime.now()
st.markdown(f"""
<div class="sedori-hero">
  <h1 class="sedori-hero-title">せどり<span class="sedori-hero-accent">管理</span></h1>
  <p class="sedori-hero-subtitle">{today.strftime('%Y年%m月%d日')} · 電脳せどり・トレンドせどり向け統合ツール</p>
</div>
""", unsafe_allow_html=True)


# ====================================================================
# サマリ(KPI 3カード)
# ====================================================================
# 計算
this_month = today.strftime("%Y-%m")
sales = data["sales"]
purchases = data["purchases"]
products_idx = {int(p["id"]): p for p in data["products"] if p.get("id")}
purchases_idx = {int(p["id"]): p for p in purchases if p.get("id")}

# 今月粗利
this_month_profit = 0
this_month_count = 0
for s in sales:
    if not (s.get("sale_date") or "").startswith(this_month):
        continue
    p = purchases_idx.get(int(s["purchase_id"]))
    if not p:
        continue
    qty = int(s["quantity"])
    sale_total = int(s["sale_price"]) * qty
    prorate_ship = round(int(p.get("shipping_in") or 0) * qty / int(p["quantity"]))
    prorate_point = round(int(p.get("point_back") or 0) * qty / int(p["quantity"]))
    cost = int(p["unit_price"]) * qty + prorate_ship - prorate_point
    fees = (int(s.get("platform_fee") or 0) + int(s.get("fba_fee") or 0)
            + int(s.get("shipping_out") or 0) + int(s.get("other_cost") or 0))
    this_month_profit += sale_total - fees - cost
    this_month_count += 1

# 在庫
sold_by_p = defaultdict(int)
for s in sales:
    sold_by_p[int(s["purchase_id"])] += int(s["quantity"])
remaining_count = 0
remaining_capital = 0
for p in purchases:
    if not p.get("id"):
        continue
    rem = int(p["quantity"]) - sold_by_p.get(int(p["id"]), 0)
    if rem > 0:
        remaining_count += rem
        remaining_capital += int(p["unit_price"]) * rem

# 候補
sourced_count = len(data["sourced"])
unlinked_sourced = sum(1 for si in data["sourced"] if not si.get("asin"))

c1, c2, c3 = st.columns(3, gap="large")
with c1:
    st.metric("今月の粗利", f"¥{this_month_profit:,}",
              delta=f"{this_month_count} 件の販売" if this_month_count else None,
              delta_color="off")
with c2:
    st.metric("未販売在庫", f"{remaining_count} 点",
              delta=f"¥{remaining_capital:,} の拘束資金" if remaining_capital else "なし",
              delta_color="off")
with c3:
    st.metric("リサーチ候補", f"{sourced_count} 件",
              delta=f"{unlinked_sourced} 件がASIN未紐づけ" if unlinked_sourced else "全て紐づけ済",
              delta_color="off")


st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True)


# ====================================================================
# クイックアクション(3カード)
# ====================================================================
st.markdown("### はじめる")
st.caption("左サイドバーから画面を選択、または下のショートカットへ")

a1, a2, a3 = st.columns(3, gap="large")
with a1:
    st.markdown("""
    <a class="sedori-card-link" href="?goto=research" target="_self">
      <div class="sedori-card">
        <div class="sedori-card-title">① Research</div>
        <div class="sedori-card-body">🔍 候補を探す</div>
        <p style="color:#2d2d2f; margin-top:8px; font-size:0.9rem; line-height: 1.6;">
          楽天 / Yahoo!ショッピングを検索して利益の出る商品を見つける。
          既存候補の一覧・販路横断比較もここから。
        </p>
        <div class="sedori-card-arrow">リサーチ画面を開く →</div>
      </div>
    </a>
    """, unsafe_allow_html=True)

with a2:
    st.markdown("""
    <a class="sedori-card-link" href="?goto=records" target="_self">
      <div class="sedori-card">
        <div class="sedori-card-title">② Input</div>
        <div class="sedori-card-body">💰 記録を入力</div>
        <p style="color:#2d2d2f; margin-top:8px; font-size:0.9rem; line-height: 1.6;">
          仕入と販売をフォームで記録。販売時は予想粗利・ROI・利益率が
          入力中にリアルタイムで更新される。
        </p>
        <div class="sedori-card-arrow">記録入力画面を開く →</div>
      </div>
    </a>
    """, unsafe_allow_html=True)

with a3:
    st.markdown("""
    <a class="sedori-card-link" href="?goto=dashboard" target="_self">
      <div class="sedori-card">
        <div class="sedori-card-title">③ Analyze</div>
        <div class="sedori-card-body">🏠 数字を見る</div>
        <p style="color:#2d2d2f; margin-top:8px; font-size:0.9rem; line-height: 1.6;">
          月次推移・販路別・カテゴリ別の利益分析。
          在庫滞留ランキング・候補Top20も一画面で俯瞰できる。
        </p>
        <div class="sedori-card-arrow">ダッシュボードを開く →</div>
      </div>
    </a>
    """, unsafe_allow_html=True)


st.markdown("<div style='height: 32px'></div>", unsafe_allow_html=True)


# ====================================================================
# 今日のTODO
# ====================================================================
st.markdown("### 今日のTODO")

todos = []
if unlinked_sourced > 0:
    todos.append(f"📎 **{unlinked_sourced} 件** のリサーチ候補がASIN未紐づけ。リサーチ画面の「候補一覧」タブで確認。")

# 長期滞留チェック
today_d = today.date()
long_held = 0
for p in purchases:
    if not p.get("id"):
        continue
    rem = int(p["quantity"]) - sold_by_p.get(int(p["id"]), 0)
    if rem <= 0:
        continue
    try:
        d = datetime.strptime(p["purchase_date"], "%Y-%m-%d").date()
        if (today_d - d).days >= 60:
            long_held += rem
    except Exception:
        pass
if long_held > 0:
    todos.append(f"⏳ **{long_held} 点** の在庫が60日以上滞留中。値下げか販路変更を検討。")

if this_month_count == 0:
    todos.append("📅 今月の販売記録がまだありません。記録入力画面からどうぞ。")

if not todos:
    st.success("✅ 対応すべき事項はありません")
else:
    for t in todos:
        st.info(t)


# ====================================================================
# サイドバー
# ====================================================================
with st.sidebar:
    st.markdown("### Status")
    if connected:
        st.success(f"Connected: {data['sheet_title']}")
        st.link_button("Spreadsheetを開く", data["sheet_url"], use_container_width=True)
    else:
        st.error(f"接続エラー: {error}")

    st.markdown("### Pages")
    st.caption("上のメニューから画面を切り替えます")

    st.markdown("### Info")
    st.caption(f"最終更新: {today.strftime('%H:%M:%S')}")
    if st.button("🔄 データ更新", use_container_width=True):
        load_overview.clear()
        st.rerun()

    season_ov, slot_ov = _resolved_bg_override()
    bg = get_background_info(season_override=season_ov, slot_override=slot_ov)
    st.markdown("### 背景情報")
    label_prefix = "🧪 プレビュー " if bg.get("is_override") else "🗓️ "
    st.caption(f"{label_prefix}{bg['season']} / {bg['time_slot']}")
    if bg["filename"]:
        st.caption(f"🖼️ {bg['filename']}")
    else:
        st.caption(f"画像未設置: `{bg['season']}　{bg['time_slot']}.png` を配置")

render_background_toggle()
