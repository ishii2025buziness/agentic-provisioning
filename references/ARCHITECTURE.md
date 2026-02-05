# Agentic Provisioning Architecture

## 設計思想

### 0. 言語非依存

このスキルは特定のプログラミング言語に依存しません。

```
SKILL.md（手順書）
├── 「何をすべきか」を記述
├── API呼び出し、判断ロジック、データ構造を定義
└── エージェントは任意の方法で実装
    ├── Bash + curl
    ├── Python + httpx
    ├── Node.js + fetch
    ├── Rust + reqwest
    └── または直接ツール呼び出し

scripts/（参考実装）
├── Pythonによる実装例
└── 必須ではない
```

### 1. Lock & Search Better (with Future-Proofing)

本システムは単なる自動化ツールではなく、**「進化し続ける自律体」** を目指します。

- **Lock**: 過去の成功を確実に再現し、退化を防ぐ基盤。
- **Search Better**: 「現在広く使われている技術」に疑いを持ち、常に明日への最適解を求める姿勢。MCPやOpenSkillsは2026年現在の強力な武器ですが、それらがゴールではない。
- **Self-Evolution**: ウェブ検索で見つかった「より優れた手段」を、エージェントが自律的に自身の実行手順に組み込み、ナレッジベースを更新する。

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub URL (入力)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  analyze_repo.py                                            │
│  - リポジトリ構造解析                                        │
│  - 要件抽出 (GPU, RAM, 言語, フレームワーク)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  knowledge.py (Lock)                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 過去の成功記録を検索                                  │   │
│  │ - 同じリポジトリの履歴                                │   │
│  │ - 類似要件のセットアップ                              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  search_better.py + Agent's WebSearch                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ウェブ検索で最新情報を取得                            │   │
│  │ - "gpu cloud pricing 2026"                          │   │
│  │ - "best python package manager 2026"                │   │
│  │ - より安いプロバイダー、より良いツールを発見           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  provision.py                                               │
│  - 最適なプロバイダーを選択                                  │
│  - 環境をプロビジョニング                                    │
│  - 結果をknowledge.pyで保存                                 │
└─────────────────────────────────────────────────────────────┘
```

### 2. エージェント非依存

このスキルはAgent Skills標準に準拠しており、以下のエージェントで動作:

- Claude Code
- Cursor
- Gemini CLI
- VS Code (Copilot)
- OpenAI Codex
- その他Agent Skills対応エージェント

### 3. プロバイダー抽象化

```python
# provision.pyの拡張例
PROVIDERS = {
    "docker-local": provision_docker_local,
    "vast-ai": provision_vast_ai,      # 将来追加
    "runpod": provision_runpod,        # 将来追加
    "hetzner": provision_hetzner,      # 将来追加
}
```

## ファイル構成

```
agentic-provisioning/
├── SKILL.md                    # スキル定義（エージェントが読む）
├── scripts/
│   ├── analyze_repo.py         # リポジトリ分析
│   ├── knowledge.py            # ナレッジベース操作
│   ├── search_better.py        # 検索クエリ生成
│   └── provision.py            # プロビジョニング実行
├── references/
│   ├── ARCHITECTURE.md         # このファイル
│   └── PROVIDERS.md            # プロバイダー情報
└── assets/
    └── knowledge/              # ナレッジストレージ
        └── index.json
```

## データフロー

### 要件抽出

```json
{
  "repo_url": "https://github.com/user/ml-project",
  "primary_language": "python",
  "frameworks": ["pytorch", "transformers"],
  "needs_gpu": true,
  "estimated_memory_gb": 16,
  "has_dockerfile": true
}
```

### ナレッジ記録

```json
{
  "id": "abc123_20260202_120000",
  "repo_url": "https://github.com/user/ml-project",
  "provider_used": "docker-local",
  "setup_steps": [
    "Cloning repository...",
    "Building image...",
    "Starting container..."
  ],
  "success": true,
  "created_at": "2026-02-02T12:00:00"
}
```

## 拡張ポイント

### 新しいプロバイダーの追加

1. `provision.py`に新しいプロビジョニング関数を追加
2. `references/PROVIDERS.md`にドキュメントを追加
3. `search_better.py`に検索クエリを追加

### 新しい言語サポート

1. `analyze_repo.py`に言語検出パターンを追加
2. `provision.py`にDockerfile生成テンプレートを追加
