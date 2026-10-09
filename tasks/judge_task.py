import json


def load_jsonl(path):
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def run_judge_task(task_cfg, executor, evaluator, reporter, dataset_cfg):
    cases = load_jsonl(dataset_cfg["path"])
    print(f"加载 {len(cases)} 条校准集")

    reports = {}
    for evaluator_name in task_cfg["evaluators"]:
        report = evaluator.evaluate(evaluator_name, cases)
        reports[evaluator_name] = report
        reporter.save_results(f"{evaluator_name}_report", report)
        print(f"  [{evaluator_name}] 完成")

    md = ["# Judge 校准报告\n"]
    if "kappa" in reports:
        r = reports["kappa"]
        md.append(f"- 样本数：{r.get('sample_size')}")
        md.append(f"- 一致率：{r.get('raw_agreement', 0):.1%}")
        md.append(f"- Kappa：{r.get('cohen_kappa', 0):.3f}")
        md.append(f"- MAE：{r.get('mae', 0):.1f}")
    reporter.save_markdown("report", "\n".join(md))