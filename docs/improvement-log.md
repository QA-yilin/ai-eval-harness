# 改进记录

每次改动留档，可追溯、可复现。

---

## 2026-10-08：Harness 封装完成

### 改动
- 新增：`core/runner.py`、`core/reporter.py`、`core/differ.py`
- 新增：`tasks/agent_task.py`、`tasks/injection_task.py`
- 新增：`config/models.yaml`、`config/datasets.yaml`、`config/tasks.yaml`
- 新增：`run.py`、`run_diff.py`、`run_all.py`
- 原因：脚本散落，无法批量，不能复现

### 前后对比
| 维度 | 封装前 | 封装后 |
|------|--------|--------|
| 任务入口 | 每类一个脚本 | 统一 run.py |
| 配置 | 硬编码 | YAML 外置 |
| 结果归档 | 散落 print | 独立 run 目录 + 配置快照 |
| 可复现 | 否 | 是 |
| 任务数 | 4 类散落 | 4 类统一 |

### 结论
Harness 化完成，四类任务全部跑通。

### 相关 run 目录
- `results/20261008_121853_rag-layered_deepseek_golden-set-8`
- `results/20261008_121905_judge-calibration_deepseek_judge-calibration-v1`
- `results/20261008_121905_agent-trajectory_deepseek_agent-tasks`
- `results/20261008_121910_prompt-injection_deepseek_injection-cases`

---

## 模板（后续改动按此格式）

### 改动
- 文件：
- 内容：
- 原因：

### 前后对比
| 指标 | Run A | Run B | 变化 |
|------|-------|-------|------|
|      |       |       |      |

### 相关 run 目录
- Run A：
- Run B：

### 结论
改善 / 退化 / 无变化