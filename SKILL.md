---
name: agentic-provisioning
description: |
  Self-optimizing provisioning system for GitHub repositories. Analyzes repos to extract requirements (language, GPU, memory), searches for optimal cloud providers via web search, provisions environments (Docker/cloud), and maintains a knowledge base of successful setups. Use when deploying code from GitHub URLs, finding cost-effective cloud providers, or reproducing development environments.
license: MIT
compatibility: Requires internet access for GitHub API and web search. Docker recommended for local provisioning.
metadata:
  author: agentic-provisioning
  version: "0.3.0"
allowed-tools: Bash WebSearch WebFetch Read Write
---

# Agentic Provisioning

GitHubリポジトリのURLを受け取り、最適な環境で自動的にプロビジョニングする。

## 稼働規律 (Guiding Principles)

1.  **Lock（成功体験の保存）**: 成功した手順をナレッジベースに保存し、再現可能にする。
2.  **Search Better（継続的改善）**: 実行前に「より良い方法」をウェブ検索し、既存のベンチマークと比較。
3.  **Anti-Obsolescence（陳腐化防止）**: **MCPやOpenSkillsといった「現在の標準」すら陳腐化する可能性を常に考慮する。** 2026年現在の定石を使いつつも、より上位のパラダイムや新技術（Post-MCP, Specialized AI-Native APIs等）の有無を必ず確認し、優位性があれば自律的に採用を検討すること。

## 使用タイミング

- GitHubリポジトリのURLが与えられ、実行環境を構築する必要がある時
- 「このリポジトリを動かして」「環境を構築して」と依頼された時
- クラウドプロバイダーの価格比較が必要な時

---

# Step 1: リポジトリ解析

## 1.1 リポジトリ情報の取得

**GitHub API呼び出し:**
```
GET https://api.github.com/repos/{owner}/{repo}
```

**抽出する情報:**
- `language`: 主要言語
- `default_branch`: デフォルトブランチ名

## 1.2 ファイルツリーの取得

**GitHub API呼び出し:**
```
GET https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1
```

**チェックするファイル:**

| ファイル | 意味 |
|----------|------|
| `requirements.txt` | Python依存関係 |
| `pyproject.toml` | Python（モダン） |
| `package.json` | Node.js |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `Dockerfile` | コンテナ定義あり |
| `docker-compose.yml` | マルチコンテナ |

## 1.3 GPU要件の検出

`requirements.txt` または `pyproject.toml` の内容を取得:
```
GET https://raw.githubusercontent.com/{owner}/{repo}/{branch}/requirements.txt
```

**GPU必要と判断するキーワード:**
```
torch, pytorch, tensorflow, jax, cuda, nvidia, cudnn,
transformers, diffusers, accelerate, vllm, triton
```

## 1.4 GPU互換性の検証（必須）

GPUが必要な場合、互換性を**プロビジョニング前に**検証する。

### CUDA Compute Capability チェック

現行のPyTorch (2.x) は **sm_70以上**（Volta世代以降）のみサポート。
以下のGPUは**使用禁止**:

| GPU | Compute Capability | 対応状況 |
|-----|-------------------|----------|
| GTX 1080 Ti | sm_61 | **非対応** |
| TITAN Xp | sm_61 | **非対応** |
| TITAN V | sm_70 | 対応 (最低ライン) |
| RTX 2080 Ti | sm_75 | 対応 |
| RTX 3060/3090 | sm_86 | **推奨** |
| RTX 4060/4090 | sm_89 | **推奨** |
| A100 | sm_80 | **推奨** |
| H100 | sm_90 | 対応 |
| L40S | sm_89 | 対応 |

**ルール:**
- `sm_70`未満のGPU → **即座に除外。選択してはならない**
- `sm_75`以上を推奨
- クラウドGPUオファーを検索する際は、GPUモデル名から世代を判定

### VRAM推定ルール

| パターン | 必要VRAM |
|---------|---------|
| モデルサイズがREADMEに記載 → その値に基づく | 記載値 × 1.2 (バッファ) |
| `transformers`, `diffusers`, `vllm` | 16GB以上 |
| `torch`, `tensorflow` (一般) | 8GB以上 |
| それ以外 | 2GB |

### プリビルドDockerイメージの探索

GPU必要なリポジトリの場合、**まずDocker Hubで公式/コミュニティのプリビルドイメージを検索**:
```
"<repo_name> docker" site:hub.docker.com
"<repo_name> docker image" site:github.com
```
プリビルドイメージがあれば、モデル・依存関係のダウンロード失敗を回避できる。

## 1.5 要件の構造化

```json
{
  "repo_url": "https://github.com/user/project",
  "repo_name": "project",
  "primary_language": "python",
  "has_dockerfile": true,
  "needs_gpu": true,
  "gpu_type": "CUDA",
  "min_compute_capability": "sm_75",
  "frameworks": ["pytorch", "transformers"],
  "estimated_vram_gb": 8,
  "estimated_memory_gb": 16,
  "entry_point": "main.py",
  "ports": [8080],
  "prebuild_docker_image": null,
  "native_api_server": null
}
```

**メモリ推定ルール:**
- `transformers`, `diffusers`, `vllm` → 16GB以上
- `torch`, `tensorflow` → 8GB以上
- それ以外 → 2GB

---

# Step 2: ナレッジベース検索（Lock）

## 2.1 ストレージ構造

ナレッジは `assets/knowledge/` に保存:
```
assets/knowledge/
├── index.json          # インデックス
└── {record_id}.json    # 個別記録
```

## 2.2 インデックス形式

```json
{
  "records": {
    "abc123_20260202": {
      "repo_url": "https://github.com/user/project",
      "provider": "docker-local",
      "success": true,
      "created_at": "2026-02-02T12:00:00"
    }
  },
  "repo_mapping": {
    "sha256_prefix_of_url": ["abc123_20260202", "def456_20260101"]
  }
}
```

## 2.3 検索ロジック

1. リポジトリURLをSHA256ハッシュ化（先頭16文字）
2. `repo_mapping`から該当するrecord_idリストを取得
3. 最新の`success: true`な記録を返す

## 2.4 類似セットアップ検索

同じリポジトリの記録がない場合、類似の要件を持つ記録を検索:
- 同じ`primary_language`
- 同じ`needs_gpu`フラグ
- 共通の`frameworks`

---

## 3.1 検索クエリ生成

要件に基づいて、**「現在の標準を超え、時代遅れになっていないか」** を検証するためのクエリを生成する:

**パラダイム検証 (Meta-Search):**
```
"state of the art AI agent deployment {current_year}"
"is MCP still the standard for AI-cloud integration?"
"better alternatives to OpenSkills or MCP in {current_year}"
```

**プロバイダー/技術検索 (Deep Search):**
```
"cheapest vps/gpu provider comparison {current_month} {current_year}"
"{requirement} best implementation approach {current_year}"
```

## 3.2 検索結果の評価と「時代遅れ」の判定

| 項目 | 例 |
|------|-----|
| プロバイダー名 | vast.ai, RunPod, Hetzner |
| 価格 | $0.25/hour, €3.49/month |
| GPU種類 | RTX 4090, A100, H100 |
| 推奨ツール | uv, ruff, docker |

## 3.3 改善判断ロジック

過去の記録と検索結果を比較:
- 価格が30%以上安い → `cost_reduction`として提案
- 新しいツールが見つかった → `tool_upgrade`として提案
- 前回から30日以上経過 → `refresh_suggestion`

## 3.4 外部スキルとMCPの動的統合

車輪の再開発を避けるため、自身のナレッジにない機能は以下の順序で探索・統合する。

### 3.4.1 推奨スキル・ソース

1.  **Personal Skill Library (優先)**: 
    - `ishii2025buziness/my-agent-skills` に収録されている高品質な自作スキル。
    - 構成:
      - `provider-hetzner`: インフラ構築
      - `collector-x-apify`: Xデータ収集
2.  **MCPサーバー**:
    - 公式のMCPサーバー（`dkruyt/mcp-hetzner`等）。
3.  **Community / Standard Skills**:
    - `agentskills.io` や `anthropics/skills`。

### 3.4.2 動的統合プロセス

```bash
# 必要な場合、自分専用のスキル集を優先的に同期
npx openskills install ishii2025buziness/my-agent-skills
npx openskills sync
```

インストール後、`npx openskills read <skill-name>` で手順をプロビジョニングフローに統合し、自律的に「最適な部品の組み合わせ」を構成する。

---

# Step 4: プロビジョニング

## 4.1 プロバイダー選択とインターフェース

プロバイダーは直接操作するのではなく、**抽象化されたインターフェース（MCP/スキル）** を介して操作することを原則とする。

| 要件 | 推奨プロバイダー / インターフェース |
|------|------------------------------------|
| CPU + 低コスト | Hetzner (via `mcp-hetzner`) |
| GPU + 低コスト | vast.ai, RunPod |
| GPU + 信頼性 | Lambda Labs, RunPod |
| GPU + ゼロインフラ | Replicate, Modal, PiAPI |
| 統合データ収集 | Apify, Firecrawl (via MCP) |
| ローカル開発 | Docker Local |

## 4.2 クラウドGPUプロビジョニング: プリフライトチェック（必須）

クラウドGPUにデプロイする前に、以下のチェックリストを**全て**実行:

### 4.2.1 リージョンフィルタ

**中国リージョン (GFW) は必ず除外。** Docker Hub, HuggingFace, PyPI等へのアクセスが制限される。

```bash
# vast.ai: 中国を除外してオファー検索
vastai search offers 'geolocation notin ["CN"] reliability > 0.99 num_gpus=1 gpu_ram >= <必要VRAM>'

# 推奨リージョン: US, CA, DE, NL, JP, SE, FI
```

**追加の地域ルール:**
- 信頼性 (`reliability`) > 0.99 を必須フィルタにする
- ネットワーク帯域 (`inet_down > 100`, `inet_up > 100`) を確認
- Certified Data Center を優先

### 4.2.2 GPU互換性チェック

Step 1.4 で定義した `min_compute_capability` に基づき、オファーのGPUモデルを検証:

```
# vast.ai: GPU名でフィルタ（古いGPUを除外）
vastai search offers 'gpu_name in ["RTX 3060","RTX 3070","RTX 3080","RTX 3090","RTX 4060","RTX 4070","RTX 4080","RTX 4090","A100","A10","L40S","H100"]'
```

**絶対に選択してはならないGPU:**
- GTX 10xx系 (1080, 1070等) — sm_61, PyTorch非対応
- TITAN Xp — sm_61, PyTorch非対応
- GTX 9xx系以前 — sm_52以下

### 4.2.3 Dockerイメージ選択

**優先順位:**
1. **プリビルドイメージ（モデル入り）** — 起動時ダウンロード不要、最も信頼性が高い
2. **公式Dockerfile** — リポジトリにDockerfileがある場合
3. **ランタイムベースイメージ** — `nvidia/cuda:12.x-runtime-ubuntu22.04`
4. ~~develイメージ~~ — **使用しない**。不必要に大きい（~10GB）

**NG:**
- `nvidia/cuda:*-devel-*` — ACE-Stepなどの推論専用ワークロードでは不要

### 4.2.4 セットアップスクリプトのエラーハンドリング

onstart/setup スクリプトには以下を必須にする:

```bash
set -euo pipefail

# モデルダウンロード後の存在確認
if [ ! -d "/path/to/expected/model" ]; then
  echo "ERROR: Model download failed" >&2
  exit 1
fi

# ファイルサイズ確認（空ファイル/部分ダウンロード防止）
MODEL_SIZE=$(du -sm /path/to/model | cut -f1)
if [ "$MODEL_SIZE" -lt <expected_min_mb> ]; then
  echo "ERROR: Model incomplete (${MODEL_SIZE}MB < expected)" >&2
  exit 1
fi

echo "SETUP_COMPLETE"
```

### 4.2.5 SSH接続の信頼性

SSHトンネルが必要な場合、`ssh` ではなく **`autossh`** を使用:

```bash
autossh -M 0 -f -N \
  -o "ServerAliveInterval=10" \
  -o "ServerAliveCountMax=3" \
  -o "ExitOnForwardFailure=yes" \
  -o "StrictHostKeyChecking=no" \
  -L <local_port>:localhost:<remote_port> \
  -p <ssh_port> <user>@<host>
```

SSHなしで直接HTTPアクセスできるプロバイダー/構成を優先する。

### 4.2.6 ポストプロビジョニング: ヘルスチェック

環境が起動したら、使用可能になるまで**ヘルスチェックで確認**:

```bash
# HTTPエンドポイントの場合
for i in $(seq 1 30); do
  if curl -sf http://localhost:<port>/health > /dev/null 2>&1; then
    echo "Service is ready"
    break
  fi
  sleep 10
done
```

**ヘルスチェック対象:**
- APIサーバーのレスポンス (200 OK)
- GPU認識確認 (`nvidia-smi` の出力)
- モデルファイルの存在確認
- CUDA互換性確認 (`python -c "import torch; print(torch.cuda.is_available())"`)

### 4.2.7 破壊的操作のガードレール

以下の操作は**実行前にユーザーに必ず確認**:

- `vastai destroy instance` — インスタンス削除
- `vastai stop instance` — インスタンス停止（ストレージは保持）
- `runpod stop/terminate pod` — Pod停止/削除

**理由:** セットアップ済み環境の削除は、モデルダウンロード・依存関係インストール等の
再構築コスト（時間・費用）が大きい。「停止」と「削除」の違いを明確にし、
ユーザーが意図しない環境消失を防ぐ。

## 4.3 Docker Local プロビジョニング

### 4.3.1 リポジトリのクローン
```bash
git clone --depth 1 {repo_url} /tmp/provision_{id}
```

### 4.3.2 Dockerfileの確認/生成

Dockerfileがない場合、言語に応じて生成:

**Python:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY requirements.txt* pyproject.toml* ./
RUN if [ -f requirements.txt ]; then uv pip install --system -r requirements.txt; fi
COPY . .
CMD ["python", "{entry_point}"]
```

**Node.js:**
```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npm", "start"]
```

**GPU対応（Python）:**
```dockerfile
FROM nvidia/cuda:12.1-runtime-ubuntu22.04
# ... 以下同様
```

### 4.3.3 ビルドと実行
```bash
docker build -t ap-{repo_name}:latest /tmp/provision_{id}
docker run -d --name ap-{instance_id} ap-{repo_name}:latest
```

**GPU対応の場合:**
```bash
docker run -d --gpus all --name ap-{instance_id} ap-{repo_name}:latest
```

---

# Step 5: 結果の記録

## 5.1 記録形式

```json
{
  "id": "{hash}_{timestamp}",
  "repo_url": "https://github.com/user/project",
  "created_at": "2026-02-02T12:00:00",
  "provider_used": "docker-local",
  "success": true,
  "setup_steps": [
    "Cloned repository",
    "Built Docker image",
    "Started container"
  ],
  "container_id": "abc123",
  "execution_time_seconds": 45.2,
  "requirements": { ... },
  "improvements_found": [ ... ]
}
```

## 5.2 保存手順

1. `assets/knowledge/index.json` を読み込み
2. 新しいrecord_idを生成: `{url_hash}_{YYYYMMDD_HHMMSS}`
3. 記録を `assets/knowledge/{record_id}.json` に保存
4. インデックスを更新して保存

---

# 環境適応ガイドライン

エージェントはターゲット環境を観察し、最適なツールを選択する:

## Python
- パッケージマネージャー: `uv` を優先（pip より 10-100x 高速）
- リンター: `ruff` を推奨（flake8, isort, black を統合）
- フォーマッター: `ruff format` または `black`

## バージョン選択
- Python: 3.11以上を推奨
- Node.js: 20 LTS以上を推奨
- 明示的な指定があればそれに従う

## GPU
- NVIDIA: CUDA 12.x を推奨
- AMD: ROCm対応イメージを使用

---

# 参考実装

`scripts/` ディレクトリにPythonによる参考実装があります。
これらは必須ではなく、エージェントは上記の手順を任意の方法で実装できます。

- [scripts/analyze_repo.py](scripts/analyze_repo.py) - リポジトリ分析
- [scripts/knowledge.py](scripts/knowledge.py) - ナレッジベース操作
- [scripts/search_better.py](scripts/search_better.py) - 検索クエリ生成
- [scripts/provision.py](scripts/provision.py) - プロビジョニング

詳細は以下を参照:
- [references/ARCHITECTURE.md](references/ARCHITECTURE.md) — 設計思想・データフロー
- [references/PROVIDERS.md](references/PROVIDERS.md) — プロバイダー情報・選択ガイド
- [references/GUARDRAILS.md](references/GUARDRAILS.md) — 障害防止ルール・事例データベース
