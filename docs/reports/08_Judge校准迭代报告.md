# 08 Judge 校准报告

> 数据集：`datasets/golden-set-19.json`（19 条，含 scoring 得分点与扣分项）
> 执行：`python run.py --task judge-calibration --dataset judge-calibration-golden`
> 判定：`core/evaluator.py::_eval_kappa`

## 1. 校准设计

把**标准答案本身**作为「模型回答」喂给 Judge（answer = gold_answer），人工基准设为 100。

设计意图：这是一次**冻结基准测试**。标准答案理应满分；如果 Judge 给不出满分，说明存在系统性低分偏差，而不是模型回答质量差。它测的是 Judge 的校准下限，不是模型能力。

## 2. 最近一次运行结果（19 条）

| 指标 | 值 | 说明 |
|---|---|---|
| 一致率 | 94.7%（18/19） | 18 条满分，1 条偏差约 20 分 |
| MAE | 1.1 | 平均绝对误差，≈21/19 |
| 证据覆盖率 | 以 `results/` 最近一次运行为准 | evidence 字段命中率 |

## 3. Kappa 的适用边界（本报告不采用 Kappa 的原因）

- 当前设计中 `human_score` 恒为 100，二值化后 human 全为 1，`pe = 1`，Cohen's Kappa 数学上退化，代码返回 0.0
- 历史记录的 0.537 → 1.0 来自早期 `judge-calibration` jsonl 集（含人工分档标注），该集已在 V2.0 废弃，不作为当前口径
- 结论：Kappa 只能在「独立双标注」上计算；在冻结基准上算 Kappa 没有统计意义，因此本报告改用 一致率 + MAE + 证据覆盖率

## 4. 已做的偏差约束

| 偏差类型 | 约束手段 |
|---|---|
| 位置偏差（标准答案与回答的呈现顺序） | 交换字段顺序复测，比较两次分值差（`tools/judge_bias_test.py`） |
| 分数漂移 | `temperature=0` + `response_format=json_object` |
| 无证据打分 | `evidence` 缺失或长度 < 2 直接判 0 |
| 评分不可解释 | 要求 reason 含计算式，如「总分 = 50 + 30 + 20 - 0 = 100」 |

## 5. 已知局限

- 未做双人独立标注，因此没有可用的 Kappa
- 19 条样本以 fact / multi_hop 为主，no_answer 与长上下文覆盖不足
- 单一 Judge 模型（deepseek-chat），跨底座一致性待补

## 6. 下一步

| 动作 | 目标 | 时间 |
|---|---|---|
| 补 30 条双人独立标注子集 | 输出真 Kappa 与一致率区间 | 12/05 |
| 换 Judge 底座复测（qwen2.5:14b） | 输出跨底座一致性 | 12/10 |
