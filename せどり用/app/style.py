"""共通カスタムCSS。各ページの先頭で apply_style() を呼ぶ。"""
import streamlit as st
from app.background import get_background_info, SEASONS, TIME_SLOTS


CUSTOM_CSS = """
<style>
/* -------- Global -------- */
.stApp {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Hiragino Sans", "Yu Gothic UI", "Meiryo", sans-serif;
    letter-spacing: 0.01em;
    background: linear-gradient(180deg, #f5faf7 0%, #f9fbfa 40%, #fafafa 100%);
}

/* ふわっとした装飾ブロブ(ヒーロー背景) */
.stApp::before {
    content: "";
    position: fixed;
    top: -200px;
    right: -200px;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(4, 120, 87, 0.10) 0%, rgba(4, 120, 87, 0) 70%);
    border-radius: 50%;
    pointer-events: none;
    z-index: 0;
}
.stApp::after {
    content: "";
    position: fixed;
    bottom: -300px;
    left: -200px;
    width: 700px;
    height: 700px;
    background: radial-gradient(circle, rgba(4, 120, 87, 0.06) 0%, rgba(4, 120, 87, 0) 70%);
    border-radius: 50%;
    pointer-events: none;
    z-index: 0;
}

/* メインコンテンツは装飾の上に */
.main .block-container {
    position: relative;
    z-index: 1;
}

/* -------- Typography -------- */
/* 背景に浮くテキスト用: text-shadowで白ふちをつけて読みやすく */
h1, h2, h3, .main .block-container > [data-testid="stMarkdownContainer"] p {
    text-shadow:
        0 1px 0 rgba(255, 255, 255, 0.7),
        0 0 12px rgba(255, 255, 255, 0.5);
}

h1 {
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
    color: #000000 !important;
    padding-top: 0 !important;
}

h2 {
    font-weight: 700 !important;
    letter-spacing: -0.01em !important;
    color: #000000 !important;
    margin-top: 1.5rem !important;
}

h3 {
    font-weight: 700 !important;
    color: #000000 !important;
}

/* 本文・キャプション・マークダウン本体 */
.stApp p, .stApp li, .stApp span {
    color: #0a0a0c;
}
.stApp small, .stCaption, [data-testid="stCaptionContainer"] {
    color: #1a1a1c !important;
    font-weight: 500 !important;
}

/* -------- Metric cards -------- */
[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #e5e5e7;
    border-radius: 12px;
    padding: 20px 24px;
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}
[data-testid="stMetric"]:hover {
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06);
    transform: translateY(-1px);
}
[data-testid="stMetricLabel"] {
    font-size: 0.85rem !important;
    color: #2d2d2f !important;
    font-weight: 500 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.9rem !important;
    font-weight: 700 !important;
    color: #0a0a0c !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stMetricDelta"] {
    font-size: 0.85rem !important;
}

/* -------- Buttons -------- */
.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    padding: 0.5rem 1.25rem;
    transition: all 0.15s ease;
    border: 1px solid #d2d2d7;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.stButton > button[kind="primary"] {
    background: #047857;
    border-color: #047857;
    color: white;
}
.stButton > button[kind="primary"]:hover {
    background: #065f46;
    border-color: #065f46;
}

/* -------- Tabs -------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid #e5e5e7;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 500;
    padding: 10px 20px;
    border-radius: 8px 8px 0 0;
}
.stTabs [aria-selected="true"] {
    color: #047857 !important;
    border-bottom: 2px solid #047857 !important;
}

/* -------- Sidebar -------- */
[data-testid="stSidebar"] {
    background-color: #fafafa;
    border-right: 1px solid #e5e5e7;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
    color: #2d2d2f !important;
    font-size: 0.8rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 1rem !important;
}

/* -------- DataFrames -------- */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e5e5e7;
}

/* -------- Inputs(白地・濃いめの枠) -------- */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input,
.stTimeInput > div > div > input,
.stTextArea textarea {
    background: #ffffff !important;
    border-radius: 10px !important;
    border: 1.5px solid #8e8e93 !important;
    color: #0a0a0c !important;
    font-weight: 500 !important;
}
/* selectbox(BaseWebベース) */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: #ffffff !important;
    border-radius: 10px !important;
    border: 1.5px solid #8e8e93 !important;
}
/* フォーカス時は primary color */
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stDateInput > div > div > input:focus,
.stTextArea textarea:focus {
    border-color: #047857 !important;
    box-shadow: 0 0 0 3px rgba(4, 120, 87, 0.15) !important;
}
/* Radio / Checkbox の周辺ラベル */
.stRadio label, .stCheckbox label {
    color: #0a0a0c !important;
    font-weight: 500 !important;
}
/* ラベル(フィールド上の項目名) */
.stApp label {
    color: #0a0a0c !important;
    font-weight: 600 !important;
}

/* -------- Info/Warning/Success/Error -------- */
.stAlert {
    background: rgba(255, 255, 255, 0.97) !important;
    border: 1px solid #e5e5e7 !important;
    border-radius: 12px !important;
    backdrop-filter: blur(4px);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
    padding: 16px 20px !important;
}
.stAlert [data-testid="stMarkdownContainer"] p {
    color: #0a0a0c !important;
    font-weight: 500 !important;
}

/* -------- Dividers -------- */
hr {
    border-color: #e5e5e7 !important;
    margin: 2rem 0 !important;
}

/* -------- Custom card class -------- */
.sedori-card {
    background: #ffffff;
    border: 1px solid #e5e5e7;
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 16px;
    transition: all 0.2s ease;
    height: 100%;
}
.sedori-card:hover {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}
.sedori-card-title {
    font-size: 0.8rem;
    color: #2d2d2f;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
}
.sedori-card-body {
    font-size: 1.5rem;
    font-weight: 700;
    color: #0a0a0c;
}

/* -------- Clickable card (linked) -------- */
a.sedori-card-link {
    display: block;
    text-decoration: none !important;
    color: inherit !important;
}
a.sedori-card-link .sedori-card {
    cursor: pointer;
    position: relative;
}
a.sedori-card-link:hover .sedori-card {
    border-color: #047857;
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(4, 120, 87, 0.12);
}
a.sedori-card-link:hover .sedori-card-title {
    color: #047857;
}
.sedori-card-arrow {
    display: inline-block;
    color: #2d2d2f;
    font-size: 0.9rem;
    margin-top: 16px;
    transition: transform 0.2s ease, color 0.2s ease;
}
a.sedori-card-link:hover .sedori-card-arrow {
    color: #047857;
    transform: translateX(4px);
}

/* -------- Hero section -------- */
.sedori-hero {
    padding: 48px 0 32px 0;
    text-align: left;
}
.sedori-hero-title {
    font-size: 2.8rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: #000000;
    margin: 0 0 8px 0;
    line-height: 1.1;
    text-shadow:
        0 1px 0 rgba(255, 255, 255, 0.8),
        0 0 16px rgba(255, 255, 255, 0.6);
}
.sedori-hero-subtitle {
    font-size: 1.15rem;
    color: #0a0a0c;
    font-weight: 600;
    margin: 0;
    text-shadow: 0 1px 0 rgba(255, 255, 255, 0.8);
}
.sedori-hero-accent {
    color: #035f45;
    text-shadow:
        0 1px 0 rgba(255, 255, 255, 0.8),
        0 0 16px rgba(255, 255, 255, 0.5);
}

/* Minimize top padding */
.main .block-container {
    padding-top: 2rem !important;
    max-width: 1200px;
}
</style>
"""


def apply_style():
    """全ページ共通のスタイルを適用する。ページ先頭で呼ぶこと。"""
    # リセットボタンで溜まったフラグを最優先で消化(全widgetより先)
    if st.session_state.pop("_bg_test_reset_trigger", False):
        st.session_state["_bg_test_season_select"] = "(自動)"
        st.session_state["_bg_test_slot_select"] = "(自動)"
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    # 背景ON/OFF 初期値(未設定なら ON)
    if "bg_enabled" not in st.session_state:
        st.session_state["bg_enabled"] = True
    if st.session_state["bg_enabled"]:
        _apply_background_image()


def render_background_toggle():
    """全ページのサイドバーで呼べる背景切替UI + テスト用強制プレビュー。"""
    with st.sidebar:
        st.markdown("### Background")
        bg_on = st.session_state.get("bg_enabled", True)
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("🌸 季節", use_container_width=True,
                         type="primary" if bg_on else "secondary",
                         key="_bg_on_btn",
                         help="季節×時間帯の背景画像を表示"):
                st.session_state["bg_enabled"] = True
                st.rerun()
        with bc2:
            if st.button("⬜ 白紙", use_container_width=True,
                         type="secondary" if bg_on else "primary",
                         key="_bg_off_btn",
                         help="背景画像を外してシンプルな白紙に"):
                st.session_state["bg_enabled"] = False
                st.rerun()

        # テストモード: 強制的に指定の季節×時間帯を表示
        with st.expander("🧪 プレビュー", expanded=False):
            st.caption("現在時刻を無視して任意の組合せを表示")
            season_options = ["(自動)"] + list(SEASONS)
            slot_options = ["(自動)"] + list(TIME_SLOTS)

            # widget key で直接管理(単一の真実)
            st.selectbox("季節", season_options, key="_bg_test_season_select")
            st.selectbox("時間帯", slot_options, key="_bg_test_slot_select")

            if st.button("自動に戻す", use_container_width=True, key="_bg_test_reset"):
                st.session_state["_bg_test_reset_trigger"] = True
                st.rerun()


def _resolved_bg_override() -> tuple:
    """sidebar の selectbox 値から override 用の季節/時間帯を返す。"""
    season_raw = st.session_state.get("_bg_test_season_select", "(自動)")
    slot_raw = st.session_state.get("_bg_test_slot_select", "(自動)")
    season_ov = None if season_raw == "(自動)" else season_raw
    slot_ov = None if slot_raw == "(自動)" else slot_raw
    return season_ov, slot_ov


def _apply_background_image():
    """背景画像(時刻/曜日/季節別)が static/backgrounds/ にあれば薄く表示する。"""
    season_ov, slot_ov = _resolved_bg_override()
    bg = get_background_info(season_override=season_ov, slot_override=slot_ov)
    if not bg["url"]:
        return
    css = f"""
    <style>
    /* 背景画像(固定、フルスクリーン、オーバーレイ薄め) */
    .stApp {{
        background-image:
            linear-gradient(180deg, rgba(247, 250, 248, 0.50) 0%, rgba(250, 250, 250, 0.50) 100%),
            url('{bg['url']}');
        background-size: cover;
        background-position: center center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}
    /* 背景は ::before ブロブよりも後ろに */
    .stApp::before, .stApp::after {{
        z-index: 0;
    }}
    /* 画像が濃い分、カードに白背景を維持して可読性を確保 */
    .sedori-card {{
        background: rgba(255, 255, 255, 0.97) !important;
        backdrop-filter: blur(4px);
    }}
    [data-testid="stMetric"] {{
        background: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(4px);
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
