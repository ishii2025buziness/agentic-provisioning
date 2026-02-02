# Agentic Provisioning

**GitHubのURLを渡すだけで、AIエージェントが最適な環境を自動構築するスキル**

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-blue)](https://agentskills.io/)

## これは何？

```
あなた: 「このリポジトリを動かして」
        https://github.com/someone/ml-project

AIエージェント:
  1. リポジトリを解析 → Python, PyTorch, GPU必要
  2. 過去の成功記録を検索 → 前回はdocker-localで成功
  3. より良い方法をウェブ検索 → vast.aiが30%安い
  4. 環境を構築 → Dockerコンテナ起動
  5. 結果を記録 → 次回はもっと速く
```

## 特徴

### 🔒 Lock（成功体験の保存）
一度成功した手順はナレッジベースに保存。次回は確実に再現できる。

### 🔍 Search Better（継続的改善）
毎回実行前にウェブ検索して「もっと良い方法」を探す。新しいプロバイダー、安い価格、速いツールを自動発見。

### 🌐 エージェント非依存
[Agent Skills標準](https://agentskills.io/)に準拠。以下のエージェントで動作：

- Claude Code
- Cursor
- Gemini CLI
- VS Code (Copilot)
- OpenAI Codex
- その他Agent Skills対応エージェント

### 📝 言語非依存
スキルの手順書（SKILL.md）はAPI呼び出しとロジックを記述。エージェントはPythonでもBashでもNode.jsでも好きな方法で実行できる。

## インストール

### OpenSkills（推奨）

```bash
# どのエージェントでも使える
npx openskills install ishii2025buziness/agentic-provisioning
npx openskills sync
```

[OpenSkills](https://github.com/numman-ali/openskills) は Agent Skills の汎用ローダー。Claude Code, Cursor, Windsurf, Aider, Codex 等で動作。

### 手動インストール

```bash
# Claude Codeの場合
git clone https://github.com/ishii2025buziness/agentic-provisioning ~/.claude/skills/agentic-provisioning

# その他のエージェント
# 各エージェントのスキルディレクトリにclone
```

## 使い方

スキルをインストール後、自然言語で依頼するだけ：

```
このリポジトリを動かして: https://github.com/user/project
```

```
https://github.com/user/ml-model をGPU環境でデプロイして
```

```
前回と同じ設定でこのリポジトリを起動して
```

## 仕組み

```
GitHub URL
    │
    ▼
┌─────────────────────────────────────┐
│ Step 1: リポジトリ解析               │
│   GitHub API → 言語、依存、GPU要件   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 2: ナレッジベース検索（Lock）    │
│   過去の成功記録を検索               │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 3: 改善検索（Search Better）    │
│   ウェブ検索で最新情報を取得         │
│   - より安いプロバイダー             │
│   - より速いツール（uv, ruff等）     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 4: プロビジョニング             │
│   Docker / クラウドで環境構築        │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 5: 結果の記録                   │
│   成功した手順をナレッジベースに保存  │
└─────────────────────────────────────┘
```

## ファイル構成

```
agentic-provisioning/
├── SKILL.md              # スキル定義（エージェントが読む手順書）
├── llms.txt              # 発見用インデックス
├── references/
│   ├── ARCHITECTURE.md   # 設計思想の詳細
│   └── PROVIDERS.md      # 対応プロバイダー情報
├── scripts/              # 参考実装（必須ではない）
│   ├── analyze_repo.py   # リポジトリ分析
│   ├── knowledge.py      # ナレッジベース操作
│   ├── search_better.py  # 検索クエリ生成
│   └── provision.py      # プロビジョニング
└── assets/
    └── knowledge/        # ナレッジストレージ
```

## 対応プロバイダー

| プロバイダー | 状態 | 用途 |
|-------------|------|------|
| Docker Local | ✅ 対応 | ローカル開発 |
| vast.ai | 🔜 予定 | GPU（低コスト） |
| RunPod | 🔜 予定 | GPU（即座） |
| Hetzner | 🔜 予定 | VPS（低コスト） |

## 設計思想

> 「前回の正解をベンチマークとして、それを超える選択肢を毎回探しに行く」

従来の自動化は「一度設定したら終わり」。このスキルは違う：

1. **再現性**：成功した手順を保存し、確実に再現
2. **進化**：毎回「もっと良い方法」を探索し、システムを陳腐化させない
3. **自律性**：ツール選択もプロバイダー選択もエージェントが判断

## ライセンス

MIT

## 関連リンク

- [Agent Skills仕様](https://agentskills.io/)
- [OpenSkills](https://github.com/numman-ali/openskills) - 汎用スキルローダー
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
