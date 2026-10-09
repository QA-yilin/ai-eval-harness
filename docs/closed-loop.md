# AI 评测闭环方法论

## 闭环链路

① 跑评测（run.py） → 产出 run_A
② 分析结果，定位问题（first_failing_layer）
③ 改配置/代码
④ 重跑评测 → 产出 run_B
⑤ 对比两次（run_diff.py）
⑥ 判断：改善 / 退化 / 无变化

## 核心原则

1. **每次只改一处**：便于归因，别一次改多个变量
2. **改动前后必须对比**：用数据说话，不凭感觉
3. **改完 A 任务要回归 B/C/D**：跑 run_all.py 确认无退化
4. **所有改动留档**：写进 improvement-log.md，可追溯

## 判断标准

| 结果 | 动作 |
|------|------|
| 指标改善 | 保留改动 |
| 指标退化 | 回滚改动 |
| 指标无变化 | 换思路，别浪费 |

## 一键回归

python run_all.py

四类任务全跑一遍，确认改动没引发退化。

## 对比两次运行

python run_diff.py --run-a results/<run_a> --run-b results/<run_b> --out diff.md

## 闭环示例（真实）

### 改进：Harness 封装

| 维度 | 封装前 | 封装后 |
|------|--------|--------|
| 任务入口 | 每类一个脚本 | 统一 run.py |
| 配置 | 硬编码 | YAML 外置 |
| 结果归档 | 散落 print | 独立 run 目录 + 配置快照 |
| 可复现 | 否 | 是 |

相关 run：

- results/20261008_121853_rag-layered_deepseek_golden-set-8
- results/20261008_121905_judge-calibration_deepseek_judge-calibration-v1
- results/20261008_121905_agent-trajectory_deepseek_agent-tasks
- results/20261008_121910_prompt-injection_deepseek_injection-cases

## 面试话术

"我做的不是一次性评测，而是评测闭环。流程是：跑评测 → 定位问题层 → 改一处 → 重跑 → run_diff 对比 → 判断改善/退化/无变化。

我实际做过的一次改进是把散落脚本封装成 Harness——封装前每类任务一个脚本、配置硬编码、结果散落 print；封装后统一入口、YAML 配置、独立 run 目录 + 配置快照。

后续如果发现检索层是瓶颈，我会用同样的闭环：换更强的检索器 → 重跑 → run_diff 对比 first_failing_layer 变化 → 判断是否保留改动。"

## 闭环的价值

| 一次性评测 | 评测闭环 |
|-----------|---------|
| 发现问题，不知道怎么改 | 改一处，重跑对比 |
| 改完不知道有没有效 | run_diff 用数据说话 |
| 改动无记录，无法追溯 | improvement-log 留档 |
| 改了 A 可能坏了 B | run_all 一键回归 |

**核心：评测不是终点，是改进的起点。**