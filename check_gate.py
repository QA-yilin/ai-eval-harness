import argparse
import json
import os
import sys
import yaml
from datetime import datetime


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_latest_run(results_dir, task_name):
    """找最新的同类 run 目录"""
    if not os.path.exists(results_dir):
        return None
    dirs = [
        d for d in os.listdir(results_dir)
        if task_name in d and os.path.isdir(os.path.join(results_dir, d))
    ]
    if not dirs:
        return None
    dirs.sort(reverse=True)
    return os.path.join(results_dir, dirs[0])


def load_run_metrics(run_dir, task_name):
    """加载某次运行的关键指标"""
    metrics = {}

    if task_name == "rag-layered":
        path = os.path.join(run_dir, "layer_summary.json")
        if os.path.exists(path):
            data = json.load(open(path, encoding="utf-8"))
            dist = data.get("first_failing_distribution", {})
            metrics["first_failing.retrieval_layer"] = dist.get("retrieval_layer", 0)
            metrics["first_failing.understanding_layer"] = dist.get("understanding_layer", 0)
            metrics["first_failing.generation_layer"] = dist.get("generation_layer", 0)

    elif task_name == "judge-calibration":
        path = os.path.join(run_dir, "kappa_report.json")
        if os.path.exists(path):
            data = json.load(open(path, encoding="utf-8"))
            metrics["cohen_kappa"] = data.get("cohen_kappa", 0)
            metrics["mae"] = data.get("mae", 0)
            metrics["raw_agreement"] = data.get("raw_agreement", 0)

    elif task_name == "agent-trajectory":
        path = os.path.join(run_dir, "agent_report.json")
        if os.path.exists(path):
            data = json.load(open(path, encoding="utf-8"))
            total = len(data)
            passed = sum(1 for r in data if r["check"]["status"] == "PASS")
            metrics["pass_rate"] = passed / total if total else 0

    elif task_name == "prompt-injection":
        path = os.path.join(run_dir, "injection_summary.json")
        if os.path.exists(path):
            data = json.load(open(path, encoding="utf-8"))
            metrics["defense_rate"] = data.get("rate", 0)

    return metrics


def check_condition(value, operator, threshold):
    if operator == ">=":
        return value >= threshold
    elif operator == "<=":
        return value <= threshold
    elif operator == ">":
        return value > threshold
    elif operator == "<":
        return value < threshold
    elif operator == "==":
        return value == threshold
    return False


def main():
    parser = argparse.ArgumentParser(description="门禁检查")
    parser.add_argument("--results-dir", default="./results")
    parser.add_argument("--gates", default="./config/gates.yaml")
    parser.add_argument("--task", default=None, help="只检查某个任务，默认全部")
    args = parser.parse_args()

    gates = load_yaml(args.gates)["gates"]
    tasks = [args.task] if args.task else list(gates.keys())

    print(f"\n{'='*60}")
    print(f"门禁检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    blocked = []
    warned = []

    for task_name in tasks:
        gate = gates[task_name]
        run_dir = find_latest_run(args.results_dir, task_name)
        if not run_dir:
            print(f"[{task_name}] 未找到运行结果，跳过")
            continue

        metrics = load_run_metrics(run_dir, task_name)
        print(f"[{task_name}]")
        print(f"  run: {os.path.basename(run_dir)}")

        for cond in gate["conditions"]:
            metric = cond["metric"]
            value = metrics.get(metric)
            if value is None:
                print(f"    - {metric}: 无数据")
                continue

            ok = check_condition(value, cond["operator"], cond["threshold"])
            status = "✅" if ok else "❌"
            print(f"    {status} {metric}: {value} {cond['operator']} {cond['threshold']}")

            if not ok:
                if cond["action"] == "block":
                    blocked.append((task_name, metric, value, cond["message"]))
                elif cond["action"] == "warn":
                    warned.append((task_name, metric, value, cond["message"]))

    print(f"\n{'='*60}")
    print(f"结果汇总")
    print(f"{'='*60}")

    if blocked:
        print(f"\n❌ 阻断项 ({len(blocked)}):")
        for t, m, v, msg in blocked:
            print(f"  - [{t}] {m}={v}: {msg}")

    if warned:
        print(f"\n⚠️  警告项 ({len(warned)}):")
        for t, m, v, msg in warned:
            print(f"  - [{t}] {m}={v}: {msg}")

    if not blocked and not warned:
        print("\n✅ 全部门禁通过")

    # 阻断则退出码 1
    sys.exit(1 if blocked else 0)


if __name__ == "__main__":
    main()