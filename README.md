# AI Eval Harness

> 四类 AI 评测任务 + 对比 + 回归 + 门禁 + 闭环 + 调度平台设计

**📖 作品集导航**： [作品集](docs/portfolio.md) | [pytest 迁移](docs/pytest-migration.md) | [闭环](docs/closed-loop.md) | [改进记录](docs/improvement-log.md) | [调度平台架构](docs/platform-architecture.md) | [门禁标准](docs/quality-gate.md)

统一 AI 评测框架，支持 RAG 分层诊断、Judge 校准、Agent 轨迹、Prompt 注入。

## 快速开始

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt

export DEEPSEEK_API_KEY=sk-xxx
python run.py --task rag-layered --model deepseek --dataset golden-set-8
```

## 支持的任务

| 任务 | 模型 | 说明 |
|------|------|------|
| `rag-layered` | deepseek | RAG 三层诊断 |
| `judge-calibration` | deepseek | Judge 校准（Kappa + MAE） |
| `agent-trajectory` | deepseek | Agent 轨迹五查 |
| `prompt-injection` | deepseek | Prompt 注入防御 |

## 核心命令

```bash
# RAG 分层诊断
python run.py --task rag-layered --model deepseek --dataset golden-set-8

# Judge 校准
python run.py --task judge-calibration --model deepseek --dataset judge-calibration-v1

# Agent 轨迹
python run.py --task agent-trajectory --model deepseek --dataset agent-tasks

# Prompt 注入
python run.py --task prompt-injection --model deepseek --dataset injection-cases
```

## 对比两次运行

```bash
python run_diff.py --run-a results/<run_a> --run-b results/<run_b> --out diff.md
```

输出指标变化 + 逐条变化。

## 架构

```
config/   → 配置外置（models / datasets / tasks）
core/     → 执行器 + 评测器 + 报告器 + 调度器 + 对比器
tasks/    → 评测任务
datasets/ → 语料 + 黄金集 + 校准集 + 注入用例
results/  → 独立 run 目录 + 配置快照
run.py    → 统一入口
```

## 核心模块

| 模块 | 职责 |
|------|------|
| `core/executor.py` | 统一调模型（DeepSeek API / Ollama） |
| `core/evaluator.py` | 统一算指标 |
| `core/reporter.py` | 统一写报告 |
| `core/runner.py` | 任务调度器 |
| `core/differ.py` | 两次运行对比 |

## 核心原则

- 先假设检索错了，再假设模型错了
- Judge 本身也是被测对象，不校准不用
- 换 Judge 只重判，换 generator 全重跑
- 配置外置，代码不动
- Harness = pytest 的 AI 评测版

## 归档机制

每次运行生成独立目录：

```
results/
└── 20261008_104621_prompt-injection_deepseek_injection-cases/
    ├── config_snapshot.json     # 本次配置快照
    ├── raw_results.json          # 原始结果
    ├── injection_summary.json    # 汇总
    └── report.md                 # Markdown 报告
```

任何时候能复现某次运行。