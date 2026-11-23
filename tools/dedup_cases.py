"""
评测用例去重 / 近重复检查（独立脚本，不依赖 repo 内部模块）。

用法：
    python tools/dedup_cases.py datasets/agent/agent-negative-cases.json
    python tools/dedup_cases.py datasets/ --recursive
"""

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path


def text_of(case):
    parts = [
        case.get("task", ""), case.get("context", ""), case.get("scenario", ""),
        case.get("question", ""), json.dumps(case.get("expected", {}), ensure_ascii=False),
    ]
    return re.sub(r"\s+", "", "".join(parts))


def load_cases(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if "tasks" in data:
        return data["tasks"]
    if "cases" in data:
        return data["cases"]
    return []


def find_duplicates(cases, threshold=0.9):
    exact, near = [], []
    texts = {c["id"]: text_of(c) for c in cases}
    for i, a in enumerate(cases):
        for b in cases[i + 1:]:
            ta, tb = texts[a["id"]], texts[b["id"]]
            if ta == tb:
                exact.append([a["id"], b["id"]])
            else:
                sim = SequenceMatcher(None, ta, tb).ratio()
                if sim >= threshold:
                    near.append({"pair": [a["id"], b["id"]], "similarity": round(sim, 3)})
    return {"exact_duplicates": exact, "near_duplicates": near}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.9)
    args = ap.parse_args()

    p = Path(args.path)
    files = list(p.rglob("*.json")) if p.is_dir() and args.recursive else [p]
    for f in files:
        cases = load_cases(f)
        print(f"== {f}  用例数={len(cases)}")
        print(json.dumps(find_duplicates(cases, args.threshold), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
