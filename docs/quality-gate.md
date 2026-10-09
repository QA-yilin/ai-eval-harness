# 门禁标准（Quality Gate）

## 一、门禁是什么

门禁 = 在 CI 里跑评测，指标不达标就不让代码合并。

**类比**：传统 CI 门禁是「单测通过率 < 100% 不让合并」，AI 评测门禁是「faithfulness < 0.9 不让合并」。

**目的**：把评测嵌入研发流程，让质量指标成为代码合并的硬约束。

## 二、四类任务的门禁指标

### 2.1 RAG 分层诊断

| 指标 | 阈值 | 动作 | 说明 |
|------|------|------|------|
| first_failing.retrieval_layer | ≤ 2 | 阻断 | 检索层失败数超 2，检索器需优化 |
| first_failing.generation_layer | ≤ 1 | 警告 | 生成层失败数超 1，检查 faithfulness |

### 2.2 Judge 校准

| 指标 | 阈值 | 动作 | 说明 |
|------|------|------|------|
| cohen_kappa | ≥ 0.6 | 警告 | Kappa 低于 0.6，Judge 可信度不足 |
| mae | ≤ 20 | 警告 | MAE 超过 20，Judge 偏差过大 |

### 2.3 Agent 轨迹

| 指标 | 阈值 | 动作 | 说明 |
|------|------|------|------|
| pass_rate | = 1.0 | 阻断 | 有 FAIL，工具/参数/顺序需检查 |

### 2.4 Prompt 注入

| 指标 | 阈值 | 动作 | 说明 |
|------|------|------|------|
| defense_rate | ≥ 0.95 | 阻断 | 防御率低于 95%，存在安全风险 |

## 三、门禁流程

```
PR 提交
    ↓
CI 触发 → 跑 run_all.py（四类任务）
    ↓
读最近一次 run 的指标
    ↓
对比 config/gates.yaml 的阈值
    ↓
    ├── 全部通过 → 允许合并
    ├── 有警告 → 允许合并，但通知
    └── 有阻断 → 禁止合并，通知 PR
```

## 四、阈值配置

所有阈值集中在 `config/gates.yaml`，改阈值不改代码。

```yaml
gates:
  rag-layered:
    conditions:
      - metric: first_failing.retrieval_layer
        operator: "<="
        threshold: 2
        action: block
      - metric: first_failing.generation_layer
        operator: "<="
        threshold: 1
        action: warn
  # ...
```

## 五、检查脚本

```bash
python check_gate.py
```

输出：

```
[rag-layered]
  run: 20261008_121853_rag-layered_deepseek_golden-set-8
    ❌ first_failing.retrieval_layer: 6 <= 2
    ✅ first_failing.generation_layer: 0 <= 1
[judge-calibration]
    ❌ cohen_kappa: 0.5 >= 0.6
    ✅ mae: 18.75 <= 20
[agent-trajectory]
    ✅ pass_rate: 1.0 >= 1.0
[prompt-injection]
    ✅ defense_rate: 1.0 >= 0.95

❌ 阻断项 (1):
  - [rag-layered] first_failing.retrieval_layer=6: 检索层失败数超过 2

⚠️  警告项 (1):
  - [judge-calibration] cohen_kappa=0.5: Kappa 低于 0.6

退出码：1（阻断）
```

## 六、CI 集成

GitHub Actions 示例：

```yaml
name: AI Quality Gate

on:
  pull_request:
    branches: [main]

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Run AI Eval
        run: python run_all.py
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
      - name: Check Quality Gate
        run: python check_gate.py
      - name: Upload Results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: eval-results
          path: results/
```

CI 流程：

1. PR 触发
2. 装依赖
3. 跑 `run_all.py`（四类任务）
4. 跑 `check_gate.py`（门禁检查）
5. 有阻断 → PR 标红，禁止合并
6. 上传评测结果作为 artifact

## 七、关键设计决策

| 决策 | 原因 |
|------|------|
| 阈值放 YAML 不放代码 | 改阈值不用改代码，非开发也能调 |
| 区分 block 和 warn | 严重问题阻断，次要问题提醒 |
| 只看最近一次 run | CI 只关心本次 PR 的结果 |
| 失败上传 artifact | 排查问题有据可查 |

## 八、门禁的价值

| 没有门禁 | 有门禁 |
|---------|--------|
| 评测跑完没人看 | 指标不达标自动阻断 |
| 质量靠人盯 | 质量靠流程 |
| 改动引入退化不知道 | CI 自动发现退化 |
| 评测和研发脱节 | 评测嵌入研发流程 |

## 九、面试话术

> "我做了门禁标准：四类任务各有阈值，CI 里跑 check_gate.py，不达标就阻断合并。比如 RAG 检索层失败数超 2 就 block，Judge Kappa 低于 0.6 就 warn。实测发现检索层失败 6 条（阻断）、Kappa 0.5（警告），说明当前 RAG 系统还需要优化。阈值集中在 config/gates.yaml，改阈值不改代码。"

## 十、一句话

门禁 = 评测指标 + 阈值 + CI 集成。不达标阻断合并，让质量成为硬约束。四类任务各有阈值，block/warn 分级，阈值配置化。