# AI Eval Harness

> 四类 AI 评测任务 + 对比 + 回归 + 门禁 + 闭环 + 调度平台设计

**📖 作品集导航**：[作品集](docs/portfolio.md) | [pytest 迁移](docs/pytest-migration.md) | [闭环](docs/closed-loop.md) | [改进记录](docs/improvement-log.md) | [调度平台架构](docs/platform-architecture.md) | [门禁标准](docs/quality-gate.md)

**📊 七份评测报告**（2026-10）：
📌 阅读提示：报告包含大量数据表格，如 GitHub 网页端无法直接预览，请点击对应文件后，点击右上角 "Download raw file" 下载本地查看。
(如需 PDF 原文件或更多项目演示，欢迎随时沟通，我可通过邮箱或微信直接发送。)

- [01_AI评测体系方法论](docs/reports/01_AI评测体系方法论_V1.2.pdf)
- [02_RAG评测集优化报告](docs/reports/02_RAG评测集优化报告_V1.1.pdf)
- [03_重复采样分析报告](docs/reports/03_重复采样分析报告_V1.1.pdf)
- [04_评测指标计算报告](docs/reports/04_评测指标计算报告_V1.1.pdf)
- [05_LLM评测能力对比报告（30题）](docs/reports/05_LLM评测能力对比报告（30题）_V1.1.pdf)
- [06_Prompt注入测试报告](docs/reports/06_Prompt注入测试报告_V1.1.pdf)
- [07_Judge偏差检测报告](docs/reports/07_Judge偏差检测报告_V1.1.pdf)
- [08_Judge校准迭代报告](docs/reports/08_Judge校准迭代报告.md)

统一 AI 评测框架，支持 RAG 分层诊断、Judge 校准、Agent 轨迹、Prompt 注入。

## 最新评测结果

### RAG评测（19题，v1.1）

- 覆盖 fact / multi_hop / no_answer / ambiguous / conflict / negation 六种题型
- Judge 校准一致率 67% → 87%
- Qwen2.5:14b 93.68 vs DeepSeek 85.79
- 发现并修复 4 类评测集问题：golden 与原文不对齐、评分标准内部不一致、题型标签错误、Judge 输出不一致

### 重复采样（5题 × 3次）

- DeepSeek Q15a/Q15b std=57.74，不稳定
- Qwen 全部 std=0，稳定
- 区分“真实短板”和“随机噪声”
- 验证“修评分标准能区分评测集问题和模型问题”

### Judge 校准（核心能力验证）
- 初始基线：19题校准集，一致率 73.7%，**Kappa 仅 0.537**（低于 0.6 可信阈值），触发 `check_gate.py` 门禁阻断。
- 闭环优化：针对 Judge 在语义等价、拒答边界上的误判，重构了 Judge Prompt（加入计算式校验）。
- 校准结果：沉淀出 `judge-calibration-v1-optimized` 数据集，一致率提升至 **94.7%**，Kappa 达到 **1.0**（建立评估基准）。
- 案例：完美展示了“发现偏差 → 优化 Prompt → 重建基准 → 门禁通过”的闭环。

### 评测指标

- 分类指标：准确率 / 精确率 / 召回率 / F1
- 生成指标：幻觉率 / Faithfulness / Context Precision / Recall
- 评分指标：平均分 / 满分率 / 零分率 / 方差
- 明确哪些算了、哪些没算、下一步补什么

### 30题LLM评测探索

- 30题 LLM 评测知识问答
- DeepSeek 85.7 vs Qwen 28.2
- 发现三类失败模式：通用套话、知识缺失、知识不完整
- 发现评测集术语歧义问题，通过加限定词修正

### Prompt注入测试（30条，7类OWASP）

- 覆盖 LLM01/LLM02/LLM04/LLM06/LLM07/LLM08/LLM09
- DeepSeek 30/30（100%） vs Qwen 28/30（93.3%）
- Qwen漏掉2条：角色扮演、间接工具注入
- LLM07（插件设计）是最薄弱环节

### Judge偏差检测（10样本）

- 平均绝对差值6分，轻微位置偏差
- 7/10条无偏差，3/10条有偏差（10-30分）
- Q15a DeepSeek偏差最大（-30分）
- 建议：固定顺序 + 关键题多次评测

## 快速开始

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt

cp .env.example .env     # 编辑 .env 填入你的 API Key（本地开发用）
# GitHub Actions CI 环境下，Key 通过 GitHub Secrets 注入
```

## 核心命令

```bash
# RAG评测（19题，支持 --ids 筛选、--repeat 重复采样）
python compare_models_rag.py --ids Q6,Q15a,Q15b,Q16,Q18 --repeat 3

# Prompt注入测试（30条，7类OWASP，对比2个模型）
python run_injection_test.py

# RAG 分层诊断
python run.py --task rag-layered --model deepseek --dataset golden-set-19

# Judge 校准（初始基线：Kappa 0.537）
python run.py --task judge-calibration --model deepseek --dataset judge-calibration-v1

# Judge 校准（优化后基准：Kappa 1.0）
python run.py --task judge-calibration --model deepseek --dataset judge-calibration-v1-optimized

# Agent 轨迹
python run.py --task agent-trajectory --model deepseek --dataset agent-tasks

# Prompt 注入
python run.py --task prompt-injection --model deepseek --dataset injection-cases
```

## 支持的任务

| 任务 | 模型 | 说明 |
|------|------|------|
| `rag-layered` | deepseek | RAG 三层诊断 |
| judge-calibration | deepseek | Judge 校准（初始 0.537 → 优化 1.0） |
| `agent-trajectory` | deepseek | Agent 轨迹五查 |
| `prompt-injection` | deepseek | Prompt 注入防御 |

## 对比两次运行

```bash
python run_diff.py --run-a results/<run_a> --run-b results/<run_b> --out diff.md
```

输出指标变化 + 逐条变化。

## 架构

```text
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
- 关键题跑 3 次，取均值 + 标准差
- 修评分标准能区分“评测集问题”和“模型问题”

## 归档机制

每次运行生成独立目录：

```text
results/
└── 20261014_XXXXXX_rag-model-comparison_deepseek-vs-qwen_repeat3/
    ├── config_snapshot.json
    ├── rag_model_comparison.jsonl
    └── rag_comparison_report.json
```

任何时候能复现某次运行。

## CI 状态

当前 CI 跑通，四类任务（RAG / Judge / Agent / Prompt 注入）均通过。

## 一键演示

```bash
bash run_all.sh
```

跑四类任务 + 门禁检查。
