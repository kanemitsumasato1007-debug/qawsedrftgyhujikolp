"""
CrowdWorks案件URL → 案件情報スクレイピングスクリプト

使い方:
  python generate_proposal.py <CrowdWorksのURL>

例:
  python generate_proposal.py https://crowdworks.jp/public/jobs/13017590

実行後、Claude Codeに「提案文を書いて」と伝えるだけで完成します。
"""

import sys
import re
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# --- パス設定 ---
BASE_DIR = Path(__file__).parent
HISTORY_DIR = BASE_DIR / "応募記録用" / "応募履歴"


def scrape_job(url: str) -> dict:
    """CrowdWorksの案件ページから情報を取得する"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja,en;q=0.9",
    }
    res = requests.get(url, headers=headers, timeout=15)
    res.raise_for_status()
    soup = BeautifulSoup(res.content, "html.parser")

    # タイトル（「の仕事の依頼」などのサフィックスを除去）
    h1 = soup.find("h1")
    raw_title = h1.get_text(strip=True) if h1 else "不明"
    title = re.sub(r"の仕事の依頼.*$", "", raw_title).strip()

    # 各セクションを取得
    sections = {}
    for h2 in soup.find_all("h2"):
        key = h2.get_text(strip=True)
        content_parts = []
        for sib in h2.find_next_siblings():
            if sib.name == "h2":
                break
            text = sib.get_text(separator="\n", strip=True)
            if text:
                content_parts.append(text)
        sections[key] = "\n".join(content_parts)

    overview = sections.get("仕事の概要", "")
    detail = sections.get("仕事の詳細", "")

    return {
        "url": url,
        "title": title,
        "overview": overview,
        "detail": detail,
    }


def save_draft(job: dict) -> Path:
    """応募履歴フォルダに下書きファイルを保存する"""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    today = date.today().strftime("%Y%m%d")
    safe_title = re.sub(r'[\\/:*?"<>|【】　]', "", job["title"])[:30].strip()
    filename = f"{today}_{safe_title}.md"
    filepath = HISTORY_DIR / filename

    content = f"""# 案件：{job['title']}

## 案件情報
- URL: {job['url']}
- クライアント：
- 報酬：
- 文字数：
- 納期：
- 応募日：{date.today().isoformat()}

## 案件概要（スクレイピング）
{job['overview']}

## 案件詳細（スクレイピング）
{job['detail']}

## 提案文
（Claude Codeが生成します）
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


def main():
    if len(sys.argv) < 2:
        print("使い方: python generate_proposal.py <CrowdWorksのURL>")
        sys.exit(1)

    url = sys.argv[1]

    print(f"案件情報を取得中... {url}")
    job = scrape_job(url)
    print(f"タイトル: {job['title']}")

    filepath = save_draft(job)
    print(f"\n下書きを保存しました: {filepath}")
    print("\nClaude Codeに「提案文を書いて」と伝えてください。")


if __name__ == "__main__":
    main()
