## 本次增量清单

| 模块 | 代码/文档 | 对应缺口 | 复用的现有资产 |
|---|---|---|---|
| Taxonomy | `docs/eval_taxonomy.md` | 场景体系化分类 | 现有三类数据集分类、题型归类 |
| Agent 负向用例 | `datasets/agent/agent-negative-cases.json` | 歧义/漏执行/错调用/答非所问/中断/逻辑混乱 | 现有 agent-tasks.json、对抗集格式 |
| 轨迹解析 | `core/agent_trace.py` | ReAct 轨迹结构化 | 现有 tools.py 执行引擎 |
| 归因断言 | `core/agent_attribution.py` | 5 类失败归因扩展为自动判定 | 现有门禁红线、Judge evidence 机制 |
| 记忆评测 | `datasets/memory/memory-cases.json` + `core/memory_check.py` + `tasks/memory_task.py` | 留存/一致性/冲突/丢失/冗余/遗忘 | 现有多轮链路、指标体系、Judge |
| Harness 调度 | `datasets/harness/harness-cases.json` + `core/harness_check.py` + `tasks/harness_task.py` | 路由/兜底/隔离/时效断言 | 现有 TTFT/分位数压测、弱网中断经验 |
| 数据治理 | `tools/dedup_cases.py` + `tools/coverage_report.py` | 去重、覆盖度、版本治理 | 现有配置化用例、重复采样 |
| 门禁 | `config/gates.yaml`（追加段） | 新模块纳入质量门禁 | 现有 gates.yaml、GitHub Actions 阻断 |

## 接入步骤

1. 把 `datasets/` 下三个 json 放入对应目录；`config/tasks.yaml` 追加 memory/harness 登记（若现有文件已有同名字段，合并而非覆盖）。
2. `core/` 四个新模块直接拷贝；`tasks/` 三个任务文件按现有任务接口对齐客户端/executor 调用名。
3. `tools/` 两个治理脚本可独立运行，先对现有数据集跑一遍去重与覆盖度。
4. 在 `config/gates.yaml` 合并新增红线段；本地回归后再推 Actions。

## 未覆盖与后续计划

- 开源框架对标（RAGAS / DeepEval / OpenCompass）：仅写结论，未跑代码。
- 平台化后端（服务接口、库表、任务队列）：属方向 B，本期不做。
- Harness 压测指标采集复用现有 performance_test(_async).py，未新增 GPU 侧指标。
