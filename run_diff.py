import argparse
import json
import os
from core.differ import Differ


def render_markdown(diff):
    md = [f"# 运行对比报告\n"]
    md.append(f"- Run A：`{diff['run_a']}`")
    md.append(f"- Run B：`{diff['run_b']}`\n")

    md.append("## 指标变化\n")
    md.append("| 指标 | Run A | Run B | 变化 | 方向 |")
    md.append("|------|-------|-------|------|------|")
    for d in diff["metrics_diff"]:
        arrow = {"improved": "↑ 改善", "regressed": "↓ 退化", "unchanged": "—"}[d["direction"]]
        md.append(f"| {d['metric']} | {d['a']} | {d['b']} | {d['delta']:+} | {arrow} |")

    md.append("\n## 逐条变化\n")
    if not diff["per_case_diff"]:
        md.append("无逐条变化。")
    else:
        md.append("| 用例 | 类型 | Run A | Run B |")
        md.append("|------|------|-------|-------|")
        for c in diff["per_case_diff"]:
            md.append(f"| {c['case_id']} | {c['type']} | {c['a']} | {c['b']} |")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="对比两次运行结果")
    parser.add_argument("--run-a", required=True, help="Run A 目录")
    parser.add_argument("--run-b", required=True, help="Run B 目录")
    parser.add_argument("--out", default=None, help="输出 Markdown 路径")
    args = parser.parse_args()

    differ = Differ(args.run_a, args.run_b)
    diff = differ.compare()

    md = render_markdown(diff)
    print(md)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n报告已写入 {args.out}")

    # 顺便写一份 json
    json_path = (args.out or "diff_report").replace(".md", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(diff, f, ensure_ascii=False, indent=2)
    print(f"JSON 已写入 {json_path}")


if __name__ == "__main__":
    main()