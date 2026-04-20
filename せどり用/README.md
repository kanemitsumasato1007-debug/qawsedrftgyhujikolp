# せどり管理ツール

電脳せどり / トレンドせどり向けの統合管理ツール。データの正本は **Google Spreadsheet**。PCのCLIから記録・リサーチし、モバイルのSheetsアプリから閲覧・コメント・共同編集できる構成。

## 構成

```
せどり用/
├── sedori.py            # 統合CLIエントリポイント
├── credentials.json     # Googleサービスアカウントキー(gitignore)
├── .env                 # APIキー・SpreadsheetID(gitignore)
├── requirements.txt
├── shared/
│   ├── config.py        # 環境変数・定数
│   ├── sheets.py        # Google Sheets ストレージ層
│   └── fees.py          # 手数料・利益計算
├── inventory/           # 在庫・利益管理
│   ├── products.py
│   ├── purchase.py
│   ├── sale.py
│   └── report.py
└── research/            # リサーチ・価格比較
    ├── rakuten.py
    ├── amazon_provider.py
    ├── scorer.py
    └── cli.py

Google Spreadsheet (=DB)
├── products       (商品マスター)
├── purchases      (仕入記録)
├── sales          (販売記録)
├── sourced_items  (楽天等の検索結果)
├── price_history  (価格履歴/トレンド)
└── dashboard      (QUERY関数で自動集計)
```

## 初回セットアップ

### 1. Google Cloud & Spreadsheet 準備
詳細は別途案内参照。概要:
- Google Cloud プロジェクト作成 → Sheets API / Drive API 有効化
- サービスアカウント作成 → JSONキーをダウンロードして `credentials.json` に配置
- 空のSpreadsheetを作成 → サービスアカウントと仲間を「編集者」で共有
- SpreadsheetのIDを `.env` に設定

### 2. 環境構築
```bash
pip install -r requirements.txt
cp .env.example .env     # 値を埋める
python sedori.py init    # Spreadsheetにタブとヘッダを自動生成
python sedori.py sheets info    # 接続確認
```

## 基本フロー

```bash
# 仕入候補のシミュレーション
python sedori.py calc --price 3980 --cost 1500 --channel "Amazon FBA" --category ゲーム --fba-fee 400

# 商品登録
python sedori.py product add --name "商品名" --category ゲーム --asin "B0XXXXXXXX"

# 仕入記録
python sedori.py purchase add --product-id 1 --date 2026-04-20 \
    --source 楽天 --store "楽天ブックス" --price 1500 --qty 5 --point 150

# 販売記録(販売手数料は自動計算)
python sedori.py sale add --purchase-id 1 --date 2026-04-22 \
    --channel "Amazon FBA" --price 3980 --qty 2 --fba-fee 400

# レポート
python sedori.py report monthly
python sedori.py report by-channel
python sedori.py report inventory       # 未販売在庫
python sedori.py report export --out sales.csv
```

## リサーチ機能

### 楽天検索 → 候補保存 → スコアリング

```bash
# 楽天市場を検索(sourced_items に保存、既知商品なら自動でAmazon比較)
python sedori.py research rakuten-search "ポケモンカード" --category ホビー --min 3000 --max 8000

# 取得候補の一覧
python sedori.py research list
python sedori.py research list --no-asin    # ASIN未紐づけのみ

# ASINを紐づけ(楽天APIはJANを返さないので手動対応)
python sedori.py product add --name "商品名" --category ホビー --asin B0XXXXXXXX
python sedori.py research link --sourced-id 3 --asin B0XXXXXXXX
```

### Amazon価格の管理

Keepa契約までは手動登録で運用。契約後は `KeepaProvider` に差し替えるだけで他のコードは変更不要。

```bash
# 手動登録
python sedori.py research amazon-set --asin B0XXXXXXXX --price 12800 --rank 1500

# 登録済みAmazon価格で保存候補を再スコアリング
python sedori.py research score --category ホビー --min-roi 20
```

### 価格推移

```bash
python sedori.py research trend --asin B0XXXXXXXX --days 30
```

### Yahoo!ショッピング検索

楽天と違い**JANコードを返してくれる**ため、Amazon自動マッチングが効く。

```bash
# キーワード検索
python sedori.py research yahoo-search "ノースフェイス ジャケット" --category アパレル --min 5000

# JANコード指定(同じ商品の最安店舗を探す)
python sedori.py research yahoo-search "_" --jan 4571657561412
```

### 販路横断の価格比較(JAN指定)

```bash
# 同じJANの商品を楽天/Yahoo!/Amazonで横並び比較(実質価格で昇順)
python sedori.py research compare --jan 4571657561412 --category アパレル
```

## GUI (Streamlit)

ブラウザで動くGUI。CLIと同じデータ(Google Sheets)を読み書きする。

```bash
# 起動
streamlit run app/main.py

# ブラウザで自動的に http://localhost:8501 が開く
# スマホから見る場合は同じWi-Fi内で表示された Network URL にアクセス
```

画面構成:
- 🔍 **リサーチ** — 楽天/Yahoo!検索、候補一覧、ASIN紐づけ、販路横断比較
- 🏠 **ダッシュボード** — KPI、月次推移、販路/カテゴリ別、在庫滞留、候補Top20
- 💰 **記録入力** — 仕入記録、販売記録(利益プレビュー付き)、商品マスター管理、履歴閲覧

## モバイルからの共有運用

- 各メンバーがGoogle Sheetsアプリで同じSpreadsheetにアクセス
- 閲覧・コメント・簡単な修正はモバイルから
- 楽天検索や販売記録など自動化はCLIから(PCを持っている人が実行)
- **dashboard** タブでQUERY関数による自動集計を閲覧

## 仕様メモ

- **金額はすべて円(整数)**。消費税は税込前提。
- **仕入原価の按分**: 仕入送料とポイント還元は販売数量で按分して原価に計上。
- **DB格納は合計値**: `sale`コマンドは単価入力 → 数量倍して保存。
- **手数料率**は `shared/fees.py` の定数で調整可能。
- **レート制限**: Sheets API は60req/分/ユーザー。楽天APIは1req/秒自動スロットル。

## トラブルシューティング

### 楽天API 403エラー (IPアドレス変更時)

自宅IPが変わると楽天API呼び出しが403で失敗します。

```bash
# 現在のグローバルIPを確認
curl -s https://api.ipify.org

# 表示されたIPを https://webservice.rakuten.co.jp/app/manage の
# アプリ編集画面「許可されたIPアドレス」に追記して保存
```

### 楽天API エンドポイント

2026年2月以降、新エンドポイント `openapi.rakuten.co.jp` を使用。
アプリタイプは **API/バックエンドサービス** を選ぶこと(Webアプリケーションタイプだと403)。

## ロードマップ

- **Phase 1 完了**: 手数料計算・仕入/販売記録・レポート
- **Phase 2 完了**: 楽天API連携・Amazon価格抽象化・差額スコアリング・価格履歴蓄積
- **Phase 3 完了**: Google Sheets バックエンド化・モバイル/複数人共有対応
- **Phase 4 (次)**: Keepa API実装、Yahoo!ショッピングAPI、メルカリ/ヤフオクスクレイピング、トレンド急上昇検知
