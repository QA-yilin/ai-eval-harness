# tasks/judge_task.py
import json
import re


def run_judge_task(task_cfg, executor, evaluator, reporter, dataset_cfg):
    # 1. 加载黄金评测集
    with open(dataset_cfg["path"], "r", encoding="utf-8") as f:
        data = json.load(f)
    cases = data["golden_set"]["items"] if "golden_set" in data else data

    print(f"加载 {len(cases)} 条黄金评测集用于 Judge 校准")

    # 2. 升级版 Judge Prompt：引入得分规则(Scoring)和上下文约束
    judge_prompt_template = """你是一个严格的评测专家。请根据以下标准给模型回答打分。

【问题】
{question}

【标准答案】
{ground_truth}

【评分标准】
{scoring}

【模型回答】
{answer}

请严格按评分标准打分，输出 JSON：
{{"score": 0-100, "reason": "打分理由", "evidence": "引用的原文证据"}}

【打分要求】
1. 先逐项核对评分标准中的每个得分点。
2. score 必须等于所有得分点之和。如果出现扣分项，要扣除。
3. 必须输出 evidence 字段，引用标准答案或评分标准中的原文，如果没有证据，score 必须为 0。
4. 只输出 JSON，不要输出任何其他内容。"""

    results = []
    for c in cases:
        # 格式化 scoring 规则（兼容 dict 和 list）
        scoring_raw = c.get("scoring", "")
        if isinstance(scoring_raw, list):
            scoring_str = "\n".join([f"- {s.get('point')} ({s.get('score')}分)" for s in scoring_raw])
            if "penalty" in c and isinstance(c["penalty"], list):
                scoring_str += "\n扣分项：\n" + "\n".join(
                    [f"- {p.get('condition')} (扣{p.get('deduct')}分)" for p in c["penalty"]])
        else:
            scoring_str = str(scoring_raw)

        # 为了测试 Judge 的客观性，我们这里故意把“标准答案”作为“模型回答”喂给它
        # 如果 Judge 是准的，它应该打 100 分；如果打不了 100 分，说明 Judge 有严重偏差。
        prompt = judge_prompt_template.format(
            question=c["question"],
            ground_truth=c["gold_answer"],
            scoring=scoring_str,
            answer=c["gold_answer"]
        )

        response = executor.call_model(prompt)

        try:
            # 容错解析 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                judge_data = json.loads(json_match.group(0))
            else:
                judge_data = json.loads(response)

            score = judge_data.get("score", 0)
            evidence = judge_data.get("evidence", "")

            # 强制证据拦截
            if not evidence or len(evidence) < 2:
                score = 0
                judge_data["reason"] = judge_data.get("reason", "") + " [拦截: 无证据引用]"

            c["judge_score"] = score
            c["human_score"] = 100  # 因为模型回答就是标准答案，人工基准理应是 100
            c["judge_evidence"] = evidence
            c["judge_reason"] = judge_data.get("reason", "")
            results.append(c)

            print(f"  [{c['id']}] Judge得分: {score} | 理由: {judge_data.get('reason', '')[:30]}...")

        except Exception as e:
            print(f"  [{c['id']}] Judge 解析失败: {e} | 原始输出: {response[:50]}")
            c["judge_score"] = 0
            c["human_score"] = 100
            c["judge_evidence"] = ""
            results.append(c)

    # 3. 计算指标
    kappa_report = evaluator.evaluate("kappa", results)

    valid_evidence_count = sum(1 for r in results if r.get("judge_evidence"))
    evidence_coverage = valid_evidence_count / len(results) if results else 0
    kappa_report["evidence_coverage"] = evidence_coverage

    reporter.save_results("kappa_report", kappa_report)
    reporter.save_results("judge_details", results)

    print(
        f"\n  [汇总] Kappa: {kappa_report.get('cohen_kappa', 0):.3f}, 证据覆盖率: {evidence_coverage:.1%}, MAE: {kappa_report.get('mae', 0):.2f}")