#!/bin/bash
set -e
# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.env"

echo "============================================================"
echo "AI Eval Harness 一键演示"
echo "============================================================"

echo -e "\n=== 1. 跑 RAG 分层评测 ==="
python run.py --task rag-layered --model deepseek --dataset golden-set-19

echo -e "\n=== 2. 跑 Judge 校准 ==="
python run.py --task judge-calibration --model deepseek --dataset judge-calibration-golden

echo -e "\n=== 3. 跑 Agent 轨迹 ==="
python run.py --task agent-trajectory --model deepseek --dataset agent-tasks

echo -e "\n=== 4. 跑 Prompt 注入 ==="
python run.py --task prompt-injection --model deepseek --dataset injection-cases

echo -e "\n=== 5. 门禁检查 ==="
python check_gate.py || true

echo -e "\n=== 6. 模型指纹防作弊校验 ==="
python check_model_drift.py || true

echo -e "\n=== 7. 最新 5 个 run 目录 ==="
ls -t results/ | head -5

echo -e "\n============================================================"
echo "演示完成"
echo "============================================================"