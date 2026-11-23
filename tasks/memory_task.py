"""
记忆评测任务（函数式接口，对齐现有 tasks/rag_task.py / judge_task.py）。

run_memory_task(task_cfg, executor, evaluator, reporter, dataset_cfg)
- 多轮消息复用 executor.call_model(messages)
- 结果结构与 reporter 约定一致：save_results 落 JSON，目录由 Reporter 按时间戳自动创建
"""

import json


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_redundant(answer, max_repeat):
    sentences = [s.strip() for s in answer.replace("！", "。").split("。") if s.strip()]
    seen = {}
    for s in sentences:
        seen[s] = seen.get(s, 0) + 1
    return any(c > max_repeat for c in seen.values())


def _check_case(case, final_answer):
    expected = case.get("expected", {})
    check_type = expected.get("check", case.get("check", "preference_retention"))
    must = expected.get("must_recall_facts", case.get("must_recall_facts", []))
    forbidden = expected.get("forbidden_facts", case.get("forbidden_facts", []))

    recalled = [f for f in must if f in final_answer]
    violated = [f for f in forbidden if f in final_answer]
    missing = [f for f in must if f not in final_answer]
    labels = []

    if check_type == "conflict_resolution":
        if violated:
            labels.append("记忆冲突")
        if missing:
            labels.append("记忆丢失")
    elif check_type == "consistency":
        if missing:
            labels.append("前后不一致")
    elif check_type == "redundancy":
        if missing:
            labels.append("记忆丢失")
        if _is_redundant(final_answer, expected.get("max_repeated_phrases", 1)):
            labels.append("冗余记忆")
    elif check_type == "boundary_forget":
        if violated:
            labels.append("记忆错乱")
    else:
        if missing:
            labels.append("记忆丢失")
        if violated:
            labels.append("记忆偏差")

    return {
        "passed": len(labels) == 0,
        "check": check_type,
        "labels": labels,
        "recalled": recalled,
        "violated": violated,
    }


def run_memory_task(task_cfg, executor, evaluator, reporter, dataset_cfg):
    data = load_json(dataset_cfg["path"])
    cases = data["cases"]
    results = []

    for c in cases:
        print(f"[{c['id']}] {c['scenario']}")
        messages = [{"role": t["role"], "content": t["content"]} for t in c["turns"]]
        final_answer = executor.call_model(messages) or ""
        check = _check_case(c, final_answer)
        results.append({
            "id": c["id"],
            "scenario": c["scenario"],
            "taxonomy": c.get("taxonomy", ["memory"]),
            "final_answer": final_answer,
            "check": check,
        })

    report = evaluator.evaluate("memory", results)

    # ==========新增一致性校验==========
    raw_count = len(results)
    report_count = report.get("sample_size", -1)
    raw_ids = {x["id"] for x in results}
    report_ids = {c["id"] for c in report.get("per_case", [])}

    print(f"\n[ConsistencyCheck][memory] raw_input={raw_count}, report.sample_size={report_count}")
    if raw_count != report_count:
        print(f"⚠️ WARNING memory：样本数量不一致 raw:{raw_count} vs report:{report_count}")
    if raw_ids != report_ids:
        print(f"⚠️ WARNING memory：用例ID集合不一致！raw_ids={raw_ids}, report_ids={report_ids}")
    # =================================

    reporter.save_results("memory_report", report)
    reporter.save_results("memory_details", results)
    reporter.save_results("raw_results", results)
    print(f"  记忆评测完成 {len(results)} 条，通过率 {report['pass_rate']:.1%}")
