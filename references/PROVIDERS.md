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

## プロバイダー選択ガイド

| 要件 | 推奨 | 理由 |
|------|------|------|
| GPU + 低コスト | vast.ai | 市場最安値 |
| GPU + 信頼性 | Lambda Labs | エンタープライズ品質 |
| CPU + 低コスト | Hetzner | 欧州最安値 |
| 開発/テスト | docker-local | 無料、即座 |
| グローバル展開 | Vultr | 多リージョン |

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
