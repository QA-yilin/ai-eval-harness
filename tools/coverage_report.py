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
    for c in cases:
        for node in c.get("taxonomy", []):
            by_node[node].append(c["id"])
        for label in c.get("failure_labels", []):
            label_dist[label] += 1
    missing = [n for n in ALL_TAXONOMY if n not in by_node]
    return {
        "total_cases": len(cases),
        "coverage": {n: len(ids) for n, ids in sorted(by_node.items())},
        "missing_nodes": missing,
        "failure_label_distribution": dict(label_dist),
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
