"""
Taxonomy 覆盖度报告（独立脚本）。

用法：
    python tools/coverage_report.py datasets/ --recursive
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

ALL_TAXONOMY = ["interaction", "planning", "tool_scheduling",
                "link_scheduling", "memory", "fault_tolerance"]


def load_cases(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("tasks") or data.get("cases") or []
    raise ValueError(f"Unsupported JSON root type: {type(data).__name__} in {path}")

def build_report(cases):
    by_node = defaultdict(list)
    label_dist = defaultdict(int)
    unlabeled_taxonomy = []
    unlabeled_fail = []
    for c in cases:
        tax = c.get("taxonomy") or []
        if tax:
            for node in tax:
                by_node[node].append(c["id"])
        else:
            unlabeled_taxonomy.append(c["id"])

        labels = c.get("fail_labels") or c.get("failure_labels") or []
        if labels:
            for label in labels:
                label_dist[label] += 1
        else:
            unlabeled_fail.append(c["id"])

    missing = [n for n in ALL_TAXONOMY if n not in by_node]
    return {
        "total_cases": len(cases),
        "coverage": {n: len(ids) for n, ids in sorted(by_node.items())},
        "missing_nodes": missing,
        "failure_label_distribution": dict(label_dist),
        "taxonomy_coverage_rate": f"{len([n for n in ALL_TAXONOMY if n in by_node])}/{len(ALL_TAXONOMY)}",
        "unlabeled_taxonomy": unlabeled_taxonomy,
        "unlabeled_fail_labels": unlabeled_fail,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--recursive", action="store_true")
    args = ap.parse_args()
    p = Path(args.path)
    files = list(p.rglob("*.json")) if p.is_dir() and args.recursive else [p]
    all_cases = []
    for f in files:
        all_cases.extend(load_cases(f))
    print(json.dumps(build_report(all_cases), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
