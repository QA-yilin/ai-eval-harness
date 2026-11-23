"""
Harness 调度评测任务（函数式接口）。

说明：路由档位、兜底模型、会话隔离、时延等分属平台/压测侧数据。
当前版本 runtime 由用例内 expected 与可选的外部回填 dict 提供；
接入真实链路时，把 runtime 替换为平台返回或 performance_test(_async).py 采集结果即可。
"""

import json


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _check_case(case, runtime):
    expected = case.get("expected", {})
    labels = []
    routing_ok = fallback_ok = isolated = None
    latency_p95 = runtime.get("latency_p95_ms")

    expected_tier = expected.get("routing_model_tier")
    if expected_tier is not None:
        routing_ok = runtime.get("routing_tier") == expected_tier
        if not routing_ok:
            labels.append("路由错误")

    if expected.get("fallback_expected"):
        fallback_ok = runtime.get("fallback_model") == expected.get("fallback_model")
        if not fallback_ok:
            labels.append("兜底未生效")

    if "session_isolation" in expected:
        isolated = bool(runtime.get("session_isolated"))
        if not isolated:
            labels.append("结果串线")

    if expected.get("adaptation_failure_detected") is not None:
        if not runtime.get("adaptation_failure_detected", expected["adaptation_failure_detected"]):
            labels.append("场景适配失效")

    max_latency = expected.get("max_p95_latency_ms")
    if max_latency is not None and latency_p95 is not None and latency_p95 > max_latency:
        labels.append("响应延迟")

    return {
        "passed": len(labels) == 0,
        "labels": labels,
        "routing_ok": routing_ok,
        "fallback_ok": fallback_ok,
        "isolated": isolated,
        "latency_p95_ms": latency_p95,
    }


def run_harness_task(task_cfg, executor, evaluator, reporter, dataset_cfg, runtime_map=None):
    data = load_json(dataset_cfg["path"])
    cases = data["cases"]
    runtime_map = runtime_map or {}
    results = []

    for c in cases:
        print(f"[{c['id']}] {c['scenario']}")
        runtime = runtime_map.get(c["id"], {})
        check = _check_case(c, runtime)
        results.append({
            "id": c["id"],
            "scenario": c["scenario"],
            "taxonomy": c.get("taxonomy", ["link_scheduling"]),
            "request": c.get("request", {}),
            "check": check,
        })

    report = evaluator.evaluate("harness", results)

    # ==========新增一致性校验==========
    raw_count = len(results)
    report_count = report.get("sample_size", -1)
    raw_ids = {x["id"] for x in results}
    report_ids = {c["id"] for c in report.get("per_case", [])}

    print(f"\n[ConsistencyCheck][harness] raw_input={raw_count}, report.sample_size={report_count}")
    if raw_count != report_count:
        print(f"⚠️ WARNING harness：样本数量不一致 raw:{raw_count} vs report:{report_count}")
    if raw_ids != report_ids:
        print(f"⚠️ WARNING harness：用例ID集合不一致！raw_ids={raw_ids}, report_ids={report_ids}")
    # =================================

    reporter.save_results("harness_report", report)
    reporter.save_results("harness_details", results)
    reporter.save_results("raw_results", results)
    print(f"  调度评测完成 {len(results)} 条，通过率 {report['pass_rate']:.1%}")
