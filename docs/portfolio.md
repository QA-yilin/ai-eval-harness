# AI 评测 Harness 作品集

## 一、项目一句话

**一个 AI 评测框架，支持 RAG 分层诊断、Judge 校准、Agent 轨迹、Prompt 注入四类任务，配置外置、任务统一、结果归档、版本可复现。**

## 二、核心能力

| 能力 | 说明 | 产出 |
|------|------|------|
| RAG 分层诊断 | 检索/理解/生成三层分别诊断，定位 first_failing_layer | 三层报告 + 根因 |
| Judge 校准 | 用人工锚点算 Cohen's Kappa，判断 Judge 可信度 | Kappa + MAE |
| Agent 轨迹 | 多步任务 + 五查（工具/参数/顺序/死循环/失败处理） | 逐条 PASS/FAIL |
| Prompt 注入 | 6 种注入手法，重点发现工具返回注入 | 防御成功率 |
| 对比功能 | 两次运行 diff，看指标变化 | diff.md |
| 回归机制 | run_all.py 一键跑四类任务 | 全量报告 |
| 门禁标准 | CI 里跑评测，不达标阻断合并 | 退出码 |
| 闭环 | 评测 → 定位 → 改动 → 重跑 → 对比 → 判断 | improvement-log |

## 三、项目架构

```
ai-eval-harness/
├── config/          # 配置外置（models / datasets / tasks / gates）
├── core/            # 核心（executor / evaluator / reporter / runner / differ）
├── tasks/           # 任务（rag / judge / agent / injection）
├── datasets/        # 数据（corpus / golden-set / 校准集 / 注入用例）
├── results/         # 独立 run 目录 + 配置快照
├── docs/            # 文档
├── run.py           # 统一入口
├── run_diff.py      # 两次运行对比
├── run_all.py       # 一键回归
├── check_gate.py    # 门禁检查
└── README.md        # 项目说明
```

## 四、文档索引

| 文档 | 内容 |
|------|------|
| [`README.md`](../README.md) | 项目说明、快速开始 |
| [`docs/pytest-migration.md`](pytest-migration.md) | pytest 架构迁移：Harness = pytest 的 AI 评测版 |
| [`docs/closed-loop.md`](closed-loop.md) | 闭环方法论：评测 → 定位 → 改动 → 重跑 → 对比 → 判断 |
| [`docs/improvement-log.md`](improvement-log.md) | 改进记录：每次改动留档 |
| [`docs/platform-architecture.md`](platform-architecture.md) | 调度平台架构：六层架构 + 14 个模块 |
| [`docs/quality-gate.md`](quality-gate.md) | 门禁标准：四类任务阈值 + CI 集成 |

## 五、演示命令

```bash
# 1. 环境准备
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
export DEEPSEEK_API_KEY=sk-xxx

# 2. 跑四类任务
python run.py --task rag-layered --model deepseek --dataset golden-set-8
python run.py --task judge-calibration --model deepseek --dataset judge-calibration-v1
python run.py --task agent-trajectory --model deepseek --dataset agent-tasks
python run.py --task prompt-injection --model deepseek --dataset injection-cases

# 3. 一键回归
python run_all.py

# 4. 对比两次运行
python run_diff.py --run-a results/<run_a> --run-b results/<run_b> --out diff.md

# 5. 门禁检查
python check_gate.py
```

## 六、面试话术导航

| 面试官可能问 | 对应文档章节 |
|-------------|-------------|
| 你为什么从传统测试转 AI 测试？ | pytest-migration.md |
| Harness 和 pytest 什么关系？ | pytest-migration.md |
| 怎么保证改动有效？ | closed-loop.md |
| 怎么做的门禁？ | quality-gate.md |
| 调度平台怎么设计的？ | platform-architecture.md |
| 四类任务分别怎么测？ | README.md + 各 task 的文档 |

## 七、核心记忆点

| 任务 | 一句话 |
|------|--------|
| RAG 分层 | 先假设检索错了，再假设模型错了 |
| Judge 校准 | Judge 本身也是被测对象，不校准不用 |
| Agent 轨迹 | 结果对不代表过程对，要五查 |
| Prompt 注入 | 工具返回内容不可信，是最危险的攻击面 |
| Harness | pytest 的 AI 评测版，10 年经验 90% 迁移 |
| 闭环 | 评测不是终点，是改进的起点 |
| 门禁 | 质量靠流程，不靠人盯 |
| 调度平台 | Harness 是执行单元，平台是管理系统 |

## 八、一句话

**ai-eval-harness：四类 AI 评测任务 + 对比 + 回归 + 门禁 + 闭环 + 调度平台设计，配置外置、任务统一、结果归档、版本可复现。**