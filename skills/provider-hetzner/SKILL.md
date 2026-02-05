---
name: provider-hetzner
description: |
  Provisioning skill for Hetzner Cloud. Uses dkruyt/mcp-hetzner for resource management. Optimized for 2026 ARM64 (CAX) instances.
allowed-tools: Bash MCP
---

# Provider: Hetzner Cloud

`dkruyt/mcp-hetzner` を使用して、Hetzner Cloud 上に最適なサーバーを構築する。

## 手順

1. **認証の確認**: `HCLOUD_TOKEN` が設定されているか確認。
2. **プランの選定**: 
   - 2026年現在の推奨は `cax11` (ARM64, 2 vCPU, 4GB RAM) 以上。
   - `mcp-hetzner` の `list_server_types` を使用して最新価格を確認。
3. **サーバー作成**: 
   - `create_server` を実行。
   - `name`: `agent-node-{project_name}`
   - `image`: `ubuntu-24.04` (ARM版)
   - `ssh_keys`: 事前に定義されたキーを使用。
4. **ファイアウォール設定**:
   - `create_firewall` で基本ポート (SSH, HTTP/S) 以外を遮断。
5. **結果の返却**: 生成された IP アドレスと作成ステータスを出力。
