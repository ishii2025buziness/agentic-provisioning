---
name: agentic-provisioning
description: |
  Self-optimizing provisioning system for GitHub repositories. Analyzes repos to extract requirements (language, GPU, memory), searches for optimal cloud providers via web search, provisions environments (Docker/cloud), and maintains a knowledge base of successful setups. Use when deploying code from GitHub URLs, finding cost-effective cloud providers, or reproducing development environments.
license: MIT
compatibility: Requires internet access for GitHub API and web search. Docker recommended for local provisioning.
metadata:
  author: agentic-provisioning
  version: "0.2.0"
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

## 1.4 要件の構造化

```json
{
  "repo_url": "https://github.com/user/project",
  "repo_name": "project",
  "primary_language": "python",
  "has_dockerfile": true,
  "needs_gpu": true,
  "gpu_type": "CUDA",
  "frameworks": ["pytorch", "transformers"],
  "estimated_memory_gb": 16,
  "entry_point": "main.py",
  "ports": [8080]
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

## 3.4 必要なスキルの動的インストールとMCP連携

2026年現在のAIエージェント環境では、車輪の再開発を避けるため、**MCP (Model Context Protocol)** サーバーと **専門特化スキル** を優先的に探索する。
[OpenSkills](https://github.com/numman-ali/openskills) を使い、以下の順序で機能を動的に拡張すること：

### 3.4.1 探索順序

1.  **MCPサーバーの探索**: 
    - 特定のプロバイダー（Hetzner, AWS等）や高度なツール（ブラウザ操作, スクレイピング）が必要な場合、まず利用可能なMCPサーバーがないか検索する。
    - 検索クエリ: `"{provider_name} mcp server official github {current_year}"`
2.  **既存スキルの探索**:
    - `agentskills.io` や GitHub 上で、目的のタスクに特化した `SKILL.md` を探す。
    - 検索クエリ: `"agent skill for {task} {current_year}"`, `site:github.com SKILL.md {task}`

### 3.4.2 動的統合プロセス

```bash
# ツールが見つかった場合、OpenSkillsでインストール
npx openskills install <github-org>/<skill-repo>
npx openskills sync
```

**判断基準と発見例:**
- **インフラ管理基盤**: Hetznerが必要なら `dkruyt/mcp-hetzner` 等の定評あるMCPを優先。
- **データ収集**: X/SNS収集なら `Apify MCP` や `Firecrawl MCP` を優先。
- **特殊処理**: PDF解析、Excel自動化など、汎用ツールより専門スキルが効率的。

インストール後、`npx openskills read <skill-name>` で手順をプロビジョニングフローに統合し、自律的に「最適な部品の組み合わせ」を構成する。

---

# Step 4: プロビジョニング

## 4.1 プロバイダー選択とインターフェース

プロバイダーは直接操作するのではなく、**抽象化されたインターフェース（MCP/スキル）** を介して操作することを原則とする。

| 要件 | 推奨プロバイダー / インターフェース |
|------|------------------------------------|
| CPU + 低コスト | Hetzner (via `mcp-hetzner`) |
| GPU + 低コスト | vast.ai, RunPod |
| 統合データ収集 | Apify, Firecrawl (via MCP) |
| ローカル開発 | Docker Local |

## 4.2 Docker Local プロビジョニング

### 4.2.1 リポジトリのクローン
```bash
git clone --depth 1 {repo_url} /tmp/provision_{id}
```

### 4.2.2 Dockerfileの確認/生成

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

### 4.2.3 ビルドと実行
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

詳細は [references/ARCHITECTURE.md](references/ARCHITECTURE.md) を参照。
