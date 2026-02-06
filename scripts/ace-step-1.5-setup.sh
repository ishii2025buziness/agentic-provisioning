#!/bin/bash
# ACE-Step 1.5 セットアップスクリプト (vast.ai用)
#
# 前提: nvidia/cuda:12.4.1-runtime-ubuntu22.04 イメージ上で実行
# 所要時間: ~5分 (モデルDL含む)
#
# 使い方:
#   1. vast.ai でインスタンス作成:
#      vastai search offers 'geolocation notin ["CN"] reliability > 0.99 num_gpus = 1 gpu_ram >= 12 dph_total <= 0.20 inet_down > 100 gpu_name in ["RTX 3060","RTX 3090","RTX 4060","RTX 4070","RTX 4080","RTX 4090","A10","L40S","A100"]' --order 'dph_total'
#      vastai create instance <offer_id> --image nvidia/cuda:12.4.1-runtime-ubuntu22.04 --disk 40
#
#   2. SSH接続してこのスクリプトを実行:
#      curl -sSL https://raw.githubusercontent.com/ishii2025buziness/agentic-provisioning/main/scripts/ace-step-1.5-setup.sh | bash
#
#   3. またはローカルにコピーして実行:
#      scp -P <port> scripts/ace-step-1.5-setup.sh root@<host>:/tmp/
#      ssh -p <port> root@<host> 'bash /tmp/ace-step-1.5-setup.sh'
#
# VRAM別の性能:
#   4-8GB   → tier1-3: LM無し/0.6B, 最大60-120秒
#   12-16GB → tier4-5: 1.7B LM, 最大240秒
#   24GB+   → tier6:   4B LM, 最大480秒, 0.69秒/30秒曲
#
# 注意:
#   - valyriantech/ace-step-1.5 Docker イメージ (173GB) は使わない
#   - ComfyUI は不要 (acestep-api が REST API を提供)

set -euo pipefail

API_PORT="${API_PORT:-8000}"
APP_DIR="${APP_DIR:-/app/ACE-Step-1.5}"

echo "=== Phase 1: GPU検証 ==="
if ! command -v nvidia-smi &> /dev/null; then
  echo "FATAL: nvidia-smi not found" >&2; exit 1
fi
GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)
echo "GPU: $GPU_INFO"
VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | tr -d ' ')
if [ "$VRAM_MB" -lt 4000 ]; then
  echo "FATAL: VRAM ${VRAM_MB}MB < 4000MB minimum" >&2; exit 1
fi

echo "=== Phase 2: システム依存関係 ==="
apt-get update -qq
apt-get install -y -qq git curl software-properties-common > /dev/null 2>&1
add-apt-repository -y ppa:deadsnakes/ppa > /dev/null 2>&1
apt-get update -qq
apt-get install -y -qq python3.11 python3.11-venv python3.11-dev > /dev/null 2>&1
python3.11 --version

echo "=== Phase 3: uv インストール ==="
if ! command -v uv &> /dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
uv --version

echo "=== Phase 4: ACE-Step 1.5 クローン ==="
if [ -d "$APP_DIR" ]; then
  echo "Already cloned at $APP_DIR"
else
  git clone --depth 1 https://github.com/ACE-Step/ACE-Step-1.5.git "$APP_DIR"
fi
cd "$APP_DIR"

echo "=== Phase 5: 依存関係インストール (uv sync) ==="
export PATH="$HOME/.local/bin:$PATH"
uv sync

echo "=== Phase 6: APIサーバー起動 ==="
echo "Models will auto-download from HuggingFace on first run (~10GB)"
nohup uv run acestep-api --host 0.0.0.0 --port "$API_PORT" > /tmp/acestep-api.log 2>&1 &
API_PID=$!
echo "API server PID: $API_PID"

echo "=== Phase 7: ヘルスチェック待機 ==="
for i in $(seq 1 60); do
  if curl -sf "http://localhost:${API_PORT}/health" > /dev/null 2>&1; then
    echo "Health check PASSED"
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "FATAL: API server crashed. Check /tmp/acestep-api.log" >&2
    tail -20 /tmp/acestep-api.log >&2
    exit 1
  fi
  echo "Waiting for API server... ($i/60) - models may be downloading"
  sleep 10
done

# 最終確認
HEALTH=$(curl -sf "http://localhost:${API_PORT}/health" 2>/dev/null || echo "FAIL")
if echo "$HEALTH" | grep -q '"ok"'; then
  echo ""
  echo "============================================"
  echo "  ACE-Step 1.5 SETUP COMPLETE"
  echo "  API: http://0.0.0.0:${API_PORT}"
  echo "  Health: ${API_PORT}/health"
  echo "  Submit: POST ${API_PORT}/release_task"
  echo "  Result: POST ${API_PORT}/query_result"
  echo "  Log: /tmp/acestep-api.log"
  echo "============================================"
else
  echo "FATAL: Health check failed after 10 minutes" >&2
  tail -30 /tmp/acestep-api.log >&2
  exit 1
fi
