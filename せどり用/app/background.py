"""背景画像の選択ロジック。季節 × 時間帯 で切り替える。

時間帯:
  朝: 5:00〜9:00
  昼: 9:01〜18:00
  夜: 18:01〜翌4:59
季節:
  春: 3,4,5月
  夏: 6,7,8月
  秋: 9,10,11月
  冬: 12,1,2月

ファイル名は「<季節>　<時間帯>.png」(全角スペース区切り)。
例: 春　朝.png / 夏　昼.png / 冬　夜.png
"""
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

APP_DIR = Path(__file__).resolve().parent
BG_DIR = APP_DIR / "static" / "backgrounds"
BG_URL_PREFIX = "app/static/backgrounds"
SUPPORTED_EXTS = ("png", "jpg", "jpeg", "webp")


def _season(now: datetime) -> str:
    m = now.month
    if m in (3, 4, 5):
        return "春"
    if m in (6, 7, 8):
        return "夏"
    if m in (9, 10, 11):
        return "秋"
    return "冬"


def _time_slot(now: datetime) -> str:
    """5:00〜9:00=朝, 9:01〜18:00=昼, それ以外=夜。9:00は朝、9:01は昼。"""
    hm = now.hour * 60 + now.minute
    if 5 * 60 <= hm <= 9 * 60:              # 5:00〜9:00
        return "朝"
    if 9 * 60 + 1 <= hm <= 18 * 60:         # 9:01〜18:00
        return "昼"
    return "夜"


def _find_file(season: str, time_slot: str) -> Optional[str]:
    if not BG_DIR.exists():
        return None
    base = f"{season}\u3000{time_slot}"  # 全角スペース
    for ext in SUPPORTED_EXTS:
        p = BG_DIR / f"{base}.{ext}"
        if p.exists():
            return p.name
    return None


SEASONS = ("春", "夏", "秋", "冬")
TIME_SLOTS = ("朝", "昼", "夜")


def get_background_info(
    now: Optional[datetime] = None,
    season_override: Optional[str] = None,
    slot_override: Optional[str] = None,
) -> dict:
    """現在時刻(または強制指定)に対応する背景画像情報を返す。"""
    now = now or datetime.now()
    season = season_override if season_override in SEASONS else _season(now)
    slot = slot_override if slot_override in TIME_SLOTS else _time_slot(now)
    fname = _find_file(season, slot)
    is_override = bool(season_override or slot_override)
    if fname:
        return {
            "season": season, "time_slot": slot,
            "filename": fname,
            "url": f"/{BG_URL_PREFIX}/{quote(fname)}",
            "is_override": is_override,
        }
    return {
        "season": season, "time_slot": slot,
        "filename": None, "url": None,
        "is_override": is_override,
    }
