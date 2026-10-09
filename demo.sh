#!/bin/bash
set -e

echo "============================================================"
echo "AI Eval Harness 一键演示"
echo "============================================================"

echo ""
echo "=== 1. 跑 RAG 分层评测 ==="
python run.py --task rag-layered --model deepseek --dataset golden-set-8

echo ""
echo "=== 2. 跑 Judge 校准 ==="
python run.py --task judge-calibration --model deepseek --dataset judge-calibration-v1

echo ""
echo "=== 3. 跑 Agent 轨迹 ==="
python run.py --task agent-trajectory --model deepseek --dataset agent-tasks

echo ""
echo "=== 4. 跑 Prompt 注入 ==="
python run.py --task prompt-injection --model deepseek --dataset injection-cases

echo ""
echo "=== 5. 门禁检查 ==="
python check_gate.py || true

echo ""
echo "=== 6. 最新 5 个 run 目录 ==="
ls -t results/ | head -5

echo ""
echo "============================================================"
echo "演示完成"
echo "============================================================"

# ============================================================
# 使用方式：
#   1. source .venv/Scripts/activate
#   2. export DEEPSEEK_API_KEY=sk-your-key-here
#   3. bash demo.sh
# ============================================================