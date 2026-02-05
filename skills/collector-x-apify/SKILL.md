---
name: collector-x-apify
description: |
  SNS post collection skill using Apify's official MCP. Fetches structure data (JSON/JSONL) from X/Twitter without hardcoding scrapers.
allowed-tools: Bash MCP
---

# Collector: X (Apify)

Apify の Twitter/X Scraper を使用して、指定されたキーワードに関連するポストを自動収集する。

## 手順

1. **認証の確認**: `APIFY_API_TOKEN` が設定されているか確認。
2. **収集パラメータの設定**:
   - `search_queries`: ユーザーが指定したキーワード。
   - `max_tweets`: 収集する最大件数（MVPでは控えめに設定）。
3. **収集実行**:
   - Apify MCP の `twitter-scraper` アクティブツールを呼び出す。
4. **データの蓄積**:
   - 取得したデータを JSONL 形式でストレージ（Hetzner Volume またはローカルディレクトリ）に保存。
   - 重複チェック（Tweet ID）を実施。
5. **完了報告**: 収集したポスト数と保存場所を報告。
