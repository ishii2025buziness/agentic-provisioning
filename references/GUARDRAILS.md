# クラウドGPUプロビジョニング: ガードレール

実際のデプロイ障害から学んだ教訓を体系化したドキュメント。
プロビジョニングの各段階で参照し、同じ失敗を繰り返さないようにする。

---

## 0. 情報収集の原則 (全工程に適用)

**検索結果を鵜呑みにしない。あらゆる情報に対して「誰が・何人が・公式か」を確認する。**

### なぜこれが最初のルールなのか

プロビジョニングの全工程（GPU選定、Docker イメージ選択、セットアップ手順の決定）において、エージェントは外部情報に依存する。その情報源の信頼性を評価しなければ、後続の全判断が汚染される。

実例: Web検索で見つけた `valyriantech/ace-step-1.5` (Docker Hub pulls 404, スター0) を無検証で採用 → 173GBイメージのpullスタック → 3セッション・数時間の浪費。**公式READMEを先に読んでいれば5分で終わっていた。**

### 情報源の優先順位

| 優先度 | 情報源 | 信頼性 | 例 |
|--------|--------|--------|-----|
| 1 | **公式リポジトリのREADME/docs** | 最高 | github.com/ace-step/ACE-Step-1.5 の README |
| 2 | **公式ドキュメントサイト** | 高 | docs.vast.ai, pytorch.org |
| 3 | **高評価のコミュニティリソース** | 中 | GitHub stars > 100, Docker pulls > 10,000 |
| 4 | **個人ブログ・記事** | 低 | 手順が古い/特定環境依存の可能性 |
| 5 | **未検証のサードパーティ** | 最低 | Docker Hub pulls < 1,000, スター 0 |

### 情報採用前のチェックリスト

```
[ ] その情報源は公式か？ (公式リポジトリ or 公式ドキュメント)
[ ] 公式でない場合、どれだけの人が使っているか？ (stars, pulls, DL数)
[ ] 公式が別の手順を推奨していないか？ (READMEを先に確認)
[ ] 情報は最新か？ (最終更新日、対象バージョン)
[ ] 複数の独立した情報源で裏付けがあるか？
```

### 検索時の行動ルール

1. **まず公式リポジトリを見る** — 検索エンジンより先に `github.com/<org>/<project>` のREADMEを読む
2. **検索結果には信頼度ラベルを付ける** — 公式/高評価/低評価/未検証を区別する
3. **「便利そう」で飛びつかない** — サードパーティの「ワンクリック」「全部入り」ソリューションほど検証が必要
4. **定量指標を確認する** — stars, pulls, downloads, last updated を必ず見る
5. **公式手順とサードパーティ手順を比較する** — 公式が十分簡単なら公式を使う

### ユーザー提案の尊重

**ユーザーがアーキテクチャを提案した場合、エージェントの「シンプルさ優先」で安易に却下しない。**

実例: ユーザーが「ComfyUIはローカル、GPUバックエンドはクラウドに分離すればいい」と提案 → エージェントが「全部1コンテナの方がシンプル」と却下 → モノリシック構成が全障害の原因に。ユーザーの分離案を最初から採用していれば数時間の浪費は起きなかった。

**ルール:**
- ユーザーの提案には必ず技術的根拠を挙げて応答する。「シンプルだから」は根拠にならない
- ユーザーの提案を却下する場合は、具体的なリスクを提示し、ユーザーが判断できるようにする
- 特にシステム分割・アーキテクチャに関するユーザーの直感は、実運用経験に基づくことが多い。尊重する

---

## 1. GPU互換性マトリクス

### PyTorch CUDA Compute Capability 対応表

| Compute Capability | GPU例 | PyTorch 2.x | 判定 |
|-------------------|-------|-------------|------|
| sm_52 | GTX 9xx | 非対応 | **禁止** |
| sm_61 | GTX 1080, TITAN Xp | 非対応 | **禁止** |
| sm_70 | TITAN V, V100 | 対応 | 最低ライン |
| sm_75 | RTX 20xx, T4 | 対応 | OK |
| sm_80 | A100 | 対応 | **推奨** |
| sm_86 | RTX 30xx, A10 | 対応 | **推奨** |
| sm_89 | RTX 40xx, L40S | 対応 | **推奨** |
| sm_90 | H100 | 対応 | **推奨** |
| sm_100 | B100/B200 | 対応 | **推奨** |

### 検証方法

クラウドインスタンス起動後、以下で確認:

```bash
python3 -c "
import torch
if torch.cuda.is_available():
    cap = torch.cuda.get_device_capability()
    name = torch.cuda.get_device_name()
    print(f'GPU: {name}, Compute Capability: sm_{cap[0]}{cap[1]}')
    if cap[0] < 7:
        print('ERROR: GPU too old for PyTorch 2.x (requires sm_70+)')
        exit(1)
else:
    print('ERROR: CUDA not available')
    exit(1)
"
```

---

## 2. リージョンブロックリスト

### 必須除外リージョン

| 国コード | 理由 |
|---------|------|
| CN (中国) | GFWによりDocker Hub, HuggingFace, PyPI等が制限/遮断 |

### vast.ai フィルタ構文

```bash
# 基本: 中国除外 + 信頼性99%以上
vastai search offers 'geolocation notin ["CN"] reliability > 0.99'

# 推奨: 安定リージョン指定 + VRAM + 価格
vastai search offers '
  geolocation in ["US","CA","DE","NL","SE","FI","JP"]
  reliability > 0.99
  num_gpus = 1
  gpu_ram >= 12
  dph_total <= 0.15
  inet_down > 100
  inet_up > 100
'
```

### SSH接続が不安定な場合

vast.aiはP2Pマーケットプレイスのため、ホストの品質にばらつきがある:
- SSH接続が確立しない場合は**30秒以内に諦めて別インスタンスを選ぶ**
- 3回連続で接続失敗 → そのホストは放棄
- Certified Data Center を優先選択

---

## 3. プリフライトチェックリスト

プロビジョニング実行前に確認:

```
[ ] GPU Compute Capability >= sm_70 (推奨 sm_75+)
[ ] リージョンが GFW 圏外
[ ] reliability > 0.99
[ ] VRAM >= モデル要件 (モデル重み + LLM + 20%余裕。公称値を信用しない)
[ ] Docker イメージ選択: プリビルド > runtime > devel (develは使わない)
[ ] onstart スクリプトにエラーハンドリングあり
[ ] モデルダウンロード後の存在確認あり
[ ] ヘルスチェックエンドポイント定義済み
[ ] 起動後にnvidia-smiで実VRAMを検証 (GPUにはVRAMバリアントが存在する)
[ ] ヘルスチェック通過後にテスト生成を実行し、結果取得まで確認
```

---

## 4. 環境構築の原則: まず公式READMEを読め

### 最重要ルール

**サードパーティのDockerイメージやラッパーツールに飛びつく前に、対象リポジトリの公式インストール手順を読む。**

多くのMLプロジェクトは公式で十分簡単なセットアップ方法を提供している。
それを無視してサードパーティ製の「便利な」Dockerイメージや、ComfyUI等のラッパーを経由すると:
- 不要なレイヤーが増え、障害の切り分けが困難になる
- イメージサイズが肥大化し、pullに時間がかかる
- 暗黙のVRAM要件やバージョン依存が隠蔽される

### サードパーティリソースの信頼性評価 (必須)

外部のDockerイメージ、ラッパーツール、フォークリポジトリを採用する前に、**必ず信頼性指標を確認する**。

| プラットフォーム | 確認項目 | 最低基準 |
|-----------------|---------|---------|
| **Docker Hub** | pulls数、スター数、最終更新日 | pulls > 1,000、スター > 0 |
| **GitHub** | スター数、フォーク数、Issue/PR活動、最終コミット | スター > 100 |
| **PyPI/npm** | 週間ダウンロード数、メンテナ情報 | 週1,000DL以上 |

**実例:** `valyriantech/ace-step-1.5` は Docker Hub で pulls 404、スター 0 だった。この時点で採用を見送るべきだった。173GBという異常なサイズも、利用者が少ないため誰もフィードバックしていなかった。

**低評価リソースのリスク:**
- テストが不十分 (暗黙のVRAM要件等が未検証)
- メンテナンスが放棄される可能性
- イメージサイズやパフォーマンスの最適化がされていない
- セキュリティリスク (サプライチェーン攻撃の可能性)

**例外:** 公式プロジェクトが推奨している場合は、指標が低くても採用可。ただしその場合も公式READMEの手順と比較すること。

### 環境構築の優先順位

1. **公式README/インストール手順に従う** — 最優先
   - 例: `git clone` + `uv sync` / `pip install -e .` → モデル自動DL
   - `uv.lock` / `requirements.txt` で再現性は担保される
   - 軽量CUDAベースイメージ (`nvidia/cuda:12.x-runtime`) 上で実行すれば十分
2. **公式Dockerfile** — リポジトリにDockerfile/docker-compose.ymlがある場合
3. **サードパーティDockerイメージ** — 上記が使えない場合の最終手段
   - **信頼性評価を先に行う** (上記の基準参照)
   - 必ずイメージサイズを確認 (Docker Hub で事前確認)
   - 20GB超のイメージはP2Pホスト (vast.ai等) でキャッシュミスリスクが高い
4. **ComfyUI等のワークフローツール** — 用途に合えば有効 (下記の判断基準を参照)

### ワークフローツール (ComfyUI等) の使い分け

ComfyUI等のビジュアルワークフローツールはそれ自体が悪いわけではない。**使い方 (デプロイ形態) と合っているかが問題。**

| 使い方 | ComfyUI | REST API直接 |
|--------|---------|-------------|
| **ローカルで試行錯誤・ワークフロー構築** | **向いてる** | 面倒 |
| **ワークフローの可視化・デバッグ** | **得意** (GUI) | なし |
| **ノード追加で後処理を拡張** | **容易** | コード変更が必要 |
| **リモートGPUへの自動デプロイ** | **不向き** | **向いてる** |
| **ヘッドレスCI/CDパイプライン** | **不向き** | **向いてる** |

**判断基準:**
- **ローカル1台で対話的に使う** → ComfyUIは良い選択。プロダクション利用も問題ない
- **リモートのクラウドGPUにヘッドレスで自動デプロイする** → REST API直接の方が確実
- **両方やりたい** → バックエンドはREST APIで構成し、ローカルでComfyUIをフロントとして被せる構成が可能

**今回の失敗の本質:** ComfyUI自体の問題ではなく、「リモートGPU + SSH越し + ヘッドレス」という合わない使い方をした。加えてサードパーティのカスタムノードのバージョン依存が衝突し、GUIなしでは障害箇所の特定が困難だった。

**将来のアーキテクチャ案:**
- マイクロサービス構成: ACE-Step API (GPU) + 後処理 (CPU) + ストレージ
- 定型パイプラインは docker-compose で宣言的に定義 (再現性確保)
- ローカルでの実験時にはComfyUIをフロントとして利用可
- クラウドGPUの確保/解放だけエージェントが担当

### 実例: ACE-Step 1.5

| 方式 | セットアップ時間 | 結果 |
|------|-----------------|------|
| valyriantech Docker (173GB) | 30分以上 (pull不能) | **失敗** |
| ComfyUI + カスタムノード (リモート) | 数時間 | **失敗** (デプロイ形態が不適切) |
| `git clone` + `uv sync` | **5分** | **成功** |

### Dockerイメージサイズの目安

| サイズ | P2Pホストでのpull | 判定 |
|--------|-------------------|------|
| ~4GB (runtime) | 1-2分 | OK |
| ~10GB (devel) | 5-10分 | 非推奨 (推論には不要) |
| 20GB超 | 15分以上、キャッシュミス多発 | **避ける** |
| 100GB超 | pullスタック/失敗の可能性大 | **使用禁止** |

推論ワークロードでは `nvidia/cuda:12.x-devel` のコンパイラは不要。
`nvidia/cuda:12.x-runtime` (~4GB) で十分。

---

## 5. セットアップスクリプトのパターン

### 正しいパターン: フェイルファスト + 検証

```bash
#!/bin/bash
set -euo pipefail

echo "=== Phase 1: Dependencies ==="
pip install torch --index-url https://download.pytorch.org/whl/cu126
python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'"

echo "=== Phase 2: Application ==="
git clone --depth 1 <repo_url> /app
cd /app && pip install -e .

echo "=== Phase 3: Model Download ==="
python -c "
from huggingface_hub import snapshot_download
snapshot_download('<model_id>', local_dir='/models/<name>')
"

# 検証: モデルの存在とサイズ
if [ ! -d "/models/<name>" ]; then
  echo "FATAL: Model directory missing" >&2; exit 1
fi
MODEL_SIZE=$(du -sm /models/<name> | cut -f1)
if [ "$MODEL_SIZE" -lt <expected_min_mb> ]; then
  echo "FATAL: Model incomplete (${MODEL_SIZE}MB)" >&2; exit 1
fi

echo "=== Phase 4: Service Start ==="
python server.py --port 8000 &

# ヘルスチェック待機
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "SETUP_COMPLETE"; exit 0
  fi
  sleep 5
done
echo "FATAL: Service failed to start within 5 minutes" >&2; exit 1
```

### 避けるべきパターン

```bash
# NG: エラーを無視してSETUP_COMPLETEを出す
pip install torch || true
python download_model.py || true
echo "SETUP_COMPLETE"  # ← モデルが無くても成功と報告
```

---

## 6. SSH接続パターン

### 推奨: autossh

```bash
# インストール
sudo apt install autossh

# 永続トンネル
autossh -M 0 -f -N \
  -o "ServerAliveInterval=10" \
  -o "ServerAliveCountMax=3" \
  -o "ExitOnForwardFailure=yes" \
  -o "StrictHostKeyChecking=no" \
  -L <local_port>:localhost:<remote_port> \
  -p <ssh_port> <user>@<host>
```

### systemdサービス化

```ini
[Unit]
Description=GPU Cloud SSH Tunnel
After=network-online.target
Wants=network-online.target

[Service]
Environment="AUTOSSH_GATETIME=0"
ExecStart=/usr/bin/autossh -M 0 -N \
  -o "ServerAliveInterval=10" \
  -o "ServerAliveCountMax=3" \
  -o "ExitOnForwardFailure=yes" \
  -L <local_port>:localhost:<remote_port> \
  -p <ssh_port> <user>@<host>
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### SSHを避ける方法

SSHトンネルは障害点が多い。可能であれば以下を優先:
- **直接HTTPアクセス** — vast.ai Direct HTTP Ports, RunPod Proxy
- **Serverless API** — Replicate, Modal, vast.ai Serverless
- **VPN/Tailscale** — SSHトンネルより安定

---

## 7. 破壊的操作のガードレール

### 確認必須の操作

| 操作 | リスク | 影響 |
|------|-------|------|
| `vastai destroy instance` | セットアップ済み環境の喪失 | 再構築に10-30分+費用 |
| `vastai stop instance` | ストレージは保持される | 再起動でリカバリ可能 |
| `runpod terminate pod` | 全データ消失 | 再構築必要 |
| `docker system prune` | ビルドキャッシュ消失 | 再ビルドに時間 |

### ルール

1. **削除系コマンドは実行前にユーザーに確認する**
2. 「停止」と「削除」の違いを明確にユーザーに説明する
3. 停止を提案されたら、まず停止 (`stop`) を選ぶ。削除 (`destroy`) は最終手段
4. セットアップに10分以上かかった環境は、削除前に必ずユーザー承認を得る

---

## 8. 障害事例データベース

### 事例1: CUDA Compute Capability非互換 (致命的)

- **症状**: PyTorchがGPUを認識しない、推論が全く動かない
- **原因**: Titan Xp (sm_61) を選択、PyTorch 2.xはsm_70+のみ対応
- **教訓**: GPUオファー選択時にCompute Capabilityを必ず検証
- **対策**: SKILL.md Step 1.4 のGPU互換性チェック

### 事例2: GFW (Great Firewall) によるネットワーク遮断

- **症状**: Docker Hub, HuggingFaceへのアクセスが極端に遅い/タイムアウト
- **原因**: 中国リージョンのインスタンスを選択
- **教訓**: 中国リージョンは必ず除外
- **対策**: `geolocation notin ["CN"]` フィルタ

### 事例3: モデルダウンロードのサイレント失敗

- **症状**: セットアップ「完了」後にモデルファイルが存在しない
- **原因**: onstart スクリプトにエラーハンドリングがない
- **教訓**: ダウンロード後の存在確認・サイズ確認を必須にする
- **対策**: セットアップスクリプトのフェイルファストパターン

### 事例4: SSHトンネル不安定

- **症状**: APIレスポンスが空 (JSONDecodeError)、接続が頻繁に切れる
- **原因**: 標準 `ssh -f -N -L` はキープアライブなし
- **教訓**: autosshを使う or SSHを避ける構成にする
- **対策**: autossh + ServerAliveInterval

### 事例5: Dockerイメージキャッシュミス

- **症状**: インスタンス起動が異常に遅い（30分以上）
- **原因**: vast.aiホストに該当Dockerイメージがキャッシュされていない
- **教訓**: プリビルドイメージを使う or 軽量ベースイメージ + pip
- **対策**: Docker Hubにプリビルドイメージがあるか先に確認

### 事例6: 確認なしのインスタンス削除

- **症状**: セットアップ済み環境が消失
- **原因**: エージェントがユーザー確認なしに `vastai destroy` を実行
- **教訓**: 破壊的操作は必ず確認
- **対策**: ガードレール7の確認ルール

### 事例7: RTX 3060 8GB/12GBバリアント不一致 (致命的)

- **症状**: vast.aiで「RTX 3060」を選択したが、実VRAMが8GBだった
- **原因**: RTX 3060には8GB版と12GB版が存在する。vast.aiのオファー名はどちらも「RTX 3060」で区別できない
- **教訓**: GPUモデル名だけでなく、起動後にnvidia-smiで実VRAMを検証する
- **対策**: プリフライトチェックにVRAM実測確認を追加。不足なら即座にdestroy

### 事例8: VRAM不足でAPI正常・タスク処理不能 (致命的)

- **症状**: APIサーバーの /health は正常応答。タスクを投入するとqueuedのまま永久に処理されない
- **原因**: ACE-Step 1.5のDiTモデル(~7.5GB)がVRAMの大半を占有。タスク処理時にLLM(Qwen3 0.6B, ~1.5GB)を追加読込→torch.OutOfMemoryError。ワーカースレッドがOOMで死亡、タスクは永久にqueued
- **教訓**: ヘルスチェック通過≠生成可能。実際にテスト生成して結果を確認するまでデプロイ完了とみなさない
- **対策**: ヘルスチェック後に必ずテスト生成を実行し、/query_resultで実際の音声データ取得を確認

### 事例9: 公称VRAM要件と実際の差異 (致命的)

- **症状**: ACE-Step 1.5は「<4GB VRAM」と公称。8GBのGPUで動くはずが動かない
- **原因**: 公称値はモデル重み単体の話。実行時はDiT(~7.5GB) + LLM(~1.5GB) + CUDAオーバーヘッド(~0.5GB) = ~9.5GB必要。valyriantech Dockerイメージは12GB+前提
- **教訓**: 公称最小VRAMを信用しない。モデル重み + LLM重み + 20%オーバーヘッドで見積もる
- **対策**: ACE-Step 1.5の実質最小VRAMは12GB。vast.aiフィルタに `gpu_ram >= 12` を設定

### 事例10: サードパーティDockerイメージ盲信による時間浪費 (根本原因)

- **症状**: 3セッション・延べ数時間を費やしても音楽生成に至らなかった
- **原因**:
  1. 公式READMEのインストール手順 (`git clone` + `uv sync`) を読まず、サードパーティのDockerイメージ (valyriantech/ace-step-1.5, 173GB) に依存
  2. ComfyUIというラッパーを不要に経由し、障害原因の切り分けが困難に
  3. 巨大イメージのpullがvast.aiのP2Pホストでスタックし続けた
- **解決**: 公式手順に従い `nvidia/cuda:12.4-runtime` (4GB) + `git clone` + `uv sync` → **5分で成功**
- **教訓**:
  - **Dockerは環境再現のベストプラクティスだが、巨大サードパーティイメージは別物**
  - プロジェクトが `uv.lock` や `requirements.txt` でバージョン固定していれば、ソースインストールも十分に再現性がある
  - MLプロジェクトのモデル重みはどの方式でもDLが必要。Dockerに焼き込む利点はキャッシュヒット時のみ
  - 対象リポジトリが自前API (REST/gRPC) を持つ場合、ComfyUI等のラッパーは不要
- **対策**: ガードレール4「環境構築の原則: まず公式READMEを読め」
