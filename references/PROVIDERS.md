# 対応プロバイダー

## 現在対応

### docker-local

ローカルDocker環境でのプロビジョニング。

**特徴:**
- コスト: 無料（ローカルリソース使用）
- 速度: 最速（ネットワーク遅延なし）
- GPU: NVIDIA Container Toolkit必要

**使用条件:**
- Dockerがインストールされている
- 十分なローカルリソース

**コマンド:**
```bash
python scripts/provision.py --provider docker-local --repo <url>
```

## 将来対応予定

### vast.ai

GPUクラウドマーケットプレイス。

**特徴:**
- 最安値のGPU（RTX 4090: ~$0.25/hour）
- オンデマンド/入札モデル
- 多様なGPUタイプ

**API情報:**
- Base URL: `https://console.vast.ai/api/v0`
- 認証: API Key

### RunPod

即座に利用可能なGPUクラウド。

**特徴:**
- A100 80GB: ~$1.89/hour
- セキュアな環境
- Serverless GPU対応

**API情報:**
- Base URL: `https://api.runpod.io`
- 認証: API Key

### Lambda Labs

MLトレーニング向けインフラ。

**特徴:**
- H100クラスター
- 長期予約で割引
- ML最適化環境

### Hetzner Cloud

コスパの高いドイツのクラウド。

**特徴:**
- CX22: 2 vCPU, 4GB RAM - €3.49/month
- 欧州リージョン
- シンプルな料金体系

**API情報:**
- Base URL: `https://api.hetzner.cloud/v1`
- 認証: Bearer Token

### Vultr

高性能クラウドコンピュート。

**特徴:**
- グローバルリージョン
- GPU対応プラン
- 時間課金

## プロバイダー接続方式 (2026年版)

特定のプロバイダーを `scripts/` に直接実装するのではなく、**MCP (Model Context Protocol)** サーバーを介して操作することを推奨します。

### 推奨 MCP サーバー一覧

| プロバイダー | 推奨 MCP / スキル | 役割 |
|-------------|-----------------|------|
| **Hetzner** | [dkruyt/mcp-hetzner](https://github.com/dkruyt/mcp-hetzner) | サーバー、FW、ボリューム管理 |
| **AWS** | [modelcontextprotocol/servers/aws](https://github.com/modelcontextprotocol/servers) | EC2, S3, IAM管理 |
| **Apify** | [Apify MCP](https://apify.com/mcp) | SNS/Webデータ収集 (X, Reddit等) |
| **Vast.ai** | [vast-ai-skill](file:///skills/provider-vast-ai) | GPUリソースの確保 |

## プロバイダーの自律的発見手順

エージェントは `SKILL.md` の指示に従い、以下のように「最新の最適解」を発見する：

1. **要件定義**: CPU/GPU、予算、リージョンを確定。
2. **ウェブ検索**: `"{provider} mcp server official"` を検索。
3. **動的統合**: `openskills install` で接続スキルを導入。

## プロバイダー選択ガイド

| 要件 | 推奨インターフェース | 理由 |
|------|------------------|------|
| **低コスト VPS** | `mcp-hetzner` | ARM(CAX)のコスパが最高 |
| **格安 GPU** | `vast-ai-skill` | マーケットプレイスの柔軟性 |
| **情報収集** | `Apify MCP` | X等の規約変更への追従性 |
| **開発/テスト** | `docker-local` | 無料、即座 |

## 検索クエリ例

エージェントは以下のようなクエリで最新情報を取得:

```
"gpu cloud pricing comparison 2026"
"vast.ai vs runpod vs lambda 2026"
"cheapest a100 rental"
"hetzner vs vultr vs digitalocean"
```

## プロバイダー追加方法

新しいプロバイダーを追加する場合:

1. **APIドキュメントを調査**
   - 認証方法
   - インスタンス作成/削除エンドポイント
   - 価格情報取得方法

2. **provision.pyに関数を追加**
   ```python
   def provision_new_provider(repo_url: str, requirements: dict) -> dict:
       # API呼び出し実装
       pass
   ```

3. **このドキュメントを更新**
