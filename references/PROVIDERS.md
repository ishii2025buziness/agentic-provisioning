# 対応プロバイダー

## Tier 1: 実装済み

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

### vast.ai

GPUクラウドマーケットプレイス（P2P）。

**特徴:**
- 最安値のGPU（RTX 3060: ~$0.06/hr, RTX 4090: ~$0.25/hr）
- オンデマンド/入札モデル
- Serverless GPU対応
- Docker/SSHアクセス

**CLI:**
```bash
pip install vastai
vastai set api-key <YOUR_KEY>
```

**オファー検索（ガードレール付き）:**
```bash
vastai search offers '
  geolocation notin ["CN"]
  reliability > 0.99
  num_gpus = 1
  gpu_ram >= 12
  dph_total <= 0.15
  inet_down > 100
  gpu_name in ["RTX 3060","RTX 3070","RTX 3080","RTX 3090","RTX 4060","RTX 4070","RTX 4080","RTX 4090","A100","A10","L40S","H100"]
'
```

**インスタンス作成:**
```bash
# プリビルドイメージ使用（推奨）
vastai create instance <offer_id> \
  --image <prebuild_image> \
  --disk 30

# カスタムセットアップ
vastai create instance <offer_id> \
  --image nvidia/cuda:12.4-runtime-ubuntu22.04 \
  --disk 30 \
  --onstart-cmd 'bash /opt/setup.sh'
```

**注意事項:**
- `geolocation notin ["CN"]` は**必須**フィルタ（GFW回避）
- GPU名でフィルタし、sm_61以下のGPU（GTX 10xx, Titan Xp）を除外
- `reliability > 0.99` で不安定ホストを除外
- `destroy` コマンドは**ユーザー確認必須**

**Serverless モード:**
- ComfyUI + ACE-Step などの専用テンプレートあり
- SSHトンネル不要、HTTP直接アクセス
- 生成物はS3自動アップロード → pre-signed URL返却

**API情報:**
- CLI: `vastai` コマンド
- Web: `https://console.vast.ai`
- ドキュメント: `https://docs.vast.ai`

---

## Tier 2: 推奨代替

### RunPod

即座に利用可能なGPUクラウド。vast.aiより高信頼。

**特徴:**
- A100 80GB: ~$1.89/hr
- セキュアな環境（Certified Data Centers）
- Serverless GPU対応
- プリビルドテンプレート豊富

**ValyrianTech Docker イメージ（ACE-Step 1.5）:**
```bash
# 全モデルプリビルド、REST API付き
# Docker Hub: valyriantech/ace-step-1.5 (~15GB)
# エンドポイント: /health, /release_task, /query_result, /v1/audio
```

**API情報:**
- Base URL: `https://api.runpod.io`
- 認証: API Key
- ドキュメント: `https://docs.runpod.io`

### Replicate (ゼロインフラ)

コード不要のML推論API。インフラ管理一切不要。

**特徴:**
- ~$0.013/生成 (ACE-Step)
- L40S GPU、~14秒/生成
- Python SDK: `replicate.run("model/name", input={...})`
- セットアップゼロ

**使い方:**
```python
import replicate
output = replicate.run("lucataco/ace-step", input={
    "prompt": "upbeat pop, female voice, 120 BPM",
    "lyrics": "[Verse]\nHello world...",
    "duration": 60
})
```

**適用場面:**
- プロトタイピング（即座に試したい）
- 少量生成（月100回以下ならクラウドGPUより安い）
- インフラ管理リソースがない場合

### Modal (サーバーレス + コード)

Python-nativeなサーバーレスGPU。

**特徴:**
- L40S GPU
- コンテナ起動時にモデルロード（`modal.enter`）
- 使用時間のみ課金
- Dockerfile不要（Pythonで環境定義）

**ドキュメント:**
- `https://modal.com/docs/examples/generate_music`

### PiAPI (ホステッドAPI)

ホステッドAPI。ACE-Step等をAPI呼び出しで利用。

**特徴:**
- text-to-music, audio-to-audio
- 19言語対応
- 無料クレジットあり
- `https://piapi.ai/ace-step`

---

## Tier 3: 汎用クラウド

### Lambda Labs

MLトレーニング向けインフラ。

**特徴:**
- H100クラスター
- 長期予約で割引
- ML最適化環境

### Hetzner Cloud

コスパの高いドイツのクラウド（CPU向け）。

**特徴:**
- CX22: 2 vCPU, 4GB RAM - EUR3.49/month
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
| **Vast.ai** | `vastai` CLI | GPUリソースの確保 |

### プロバイダーの自律的発見手順

1. **要件定義**: CPU/GPU、予算、リージョンを確定。
2. **ウェブ検索**: `"{provider} mcp server official"` を検索。
3. **動的統合**: `openskills install` で接続スキルを導入。

---

## プロバイダー選択ガイド

| 要件 | 推奨 | 理由 |
|------|------|------|
| GPU + 最安値 | vast.ai | P2Pマーケットプレイス最安 |
| GPU + 信頼性 | RunPod | Certified Data Centers |
| GPU + ゼロ運用 | Replicate | インフラ管理不要 |
| GPU + サーバーレス | Modal | Python-native、使用分のみ課金 |
| CPU + 低コスト (MCP) | `mcp-hetzner` | ARM(CAX)のコスパが最高 |
| 情報収集 | `Apify MCP` | X等の規約変更への追従性 |
| 開発/テスト | docker-local | 無料、即座 |

## 検索クエリ例

エージェントは以下のようなクエリで最新情報を取得:

```
"gpu cloud pricing comparison 2026"
"vast.ai vs runpod vs lambda 2026"
"cheapest a100 rental"
"<model_name> docker image" site:hub.docker.com
"<model_name> api" site:replicate.com
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
