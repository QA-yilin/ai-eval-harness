"""
Agent 负向评测任务（在现有 agent_task.py 的 run_simple_agent 基础上扩展）。

字段对齐现有 agent-tasks.json：id / task / tools / expected_steps / scenario；
新增 clarification_required / fail_labels / taxonomy 用于归因与覆盖度统计。
执行循环与工具调用完全复用 core.tools.ToolRegistry，不引入新工具。
"""

import json
import re
import time
from core.tools import ToolRegistry

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_action(text):
    match = re.search(r"Action:\s*(\w+)\((.*?)\)", text, re.DOTALL)
    if not match:
        return None, None
    tool_name = match.group(1).strip()
    args_str = match.group(2).strip()
    try:
        args_dict = json.loads(args_str) if args_str else {}
    except json.JSONDecodeError:
        args_dict = {}
        for kv in args_str.split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                args_dict[k.strip()] = v.strip().strip('"\'')
    return tool_name, args_dict


def run_simple_agent(task_item, executor, max_turns=5):
    system_prompt = (
        "你是一个智能助手。可用工具及参数：\n"
        "1. get_weather(city)\n"
        "2. calculate_exchange(amount, currency)\n\n"
        "信息不足时先向用户澄清，不要臆造城市、金额或币种。请严格按格式输出：\n"
        "Thought: 思考过程\n"
        "Action: 工具名({参数JSON})\n"
        "...循环...\n"
        "Final Answer: 最终回答"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_item["task"]}
    ]

    steps = []
    turn_durations = {}
    response = ""

    for turn in range(max_turns):
        turn_start = time.perf_counter()
        response = executor.call_model(messages)
        if not response:
            turn_durations[turn] = time.perf_counter() - turn_start
            break

        if "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
            steps.append({"type": "Action", "tool": "reply", "args": {"content": final_answer}, "observation": "END"})
            turn_durations[turn] = time.perf_counter() - turn_start
            break

        tool_name, tool_args = parse_action(response)
        if not tool_name:
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": "Observation: 格式错误。必须使用 Action: tool_name({args}) 的格式。"})
            steps.append({"type": "FormatError", "raw": response})
            turn_durations[turn] = time.perf_counter() - turn_start
            continue

        observation = ToolRegistry.execute(tool_name, tool_args)
        steps.append({"type": "Action", "tool": tool_name, "args": tool_args, "observation": observation})
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": f"Observation: {observation}"})
        turn_durations[turn] = time.perf_counter() - turn_start

    return {
        "id": task_item["id"],
        "steps": steps,
        "expected_steps": task_item.get("expected_steps", []),
        "tools": task_item.get("tools", []),
        "clarification_required": task_item.get("clarification_required", False),
        "raw_answer": response,
        "turn_durations": turn_durations,
    }


def run_agent_negative_task(task_cfg, executor, evaluator, reporter, dataset_cfg):
    tasks = load_json(dataset_cfg["path"])["tasks"]
    eval_input_list = []
    traj_map = {}

    for t in tasks:
        print(f"[{t['id']}] {t['task']}")
        trajectory = run_simple_agent(t, executor)
        # 关键：把原始数据集的真值 expected_steps / tools白名单一并传给evaluator
        item = {
            "id": t["id"],
            "trajectory": trajectory,
            "expected_steps": t.get("expected_steps", []),
            "tools": t.get("tools", []),
            "clarification_required": t.get("clarification_required", False)
        }

        eval_input_list.append(item)
        traj_map[t["id"]] = trajectory

    # 批量一次性评测
    eval_result = evaluator.evaluate("agent_negative", eval_input_list)
    per_case_list = eval_result.get("per_case", [])

    # ==========新增一致性校验==========
    raw_count = len(eval_input_list)
    report_count = eval_result.get("sample_size", -1)
    raw_ids = {x.get("id") for x in eval_input_list if x.get("id") is not None}
    report_ids = {c.get("id") for c in per_case_list if c.get("id") is not None}

    print(f"\n[ConsistencyCheck][agent‑negative] raw_input={raw_count}, report.sample_size={report_count}")
    if raw_count != report_count:
        print(f"⚠️ WARNING agent‑negative：样本数量不一致 raw:{raw_count} vs report:{report_count}")
    if raw_ids != report_ids:
        print(f"⚠️ WARNING agent‑negative：用例ID集合不一致！raw_ids={raw_ids}, report_ids={report_ids}")
    # =================================

    # 回填原始trajectory到评测结果；如果case已经自带trajectory，则不再覆盖（保护离线测试用例）
    for case in per_case_list:
        cid = case.get("id")
        if cid in traj_map and "trajectory" not in case:
            case["trajectory"] = traj_map[cid]

    reporter.save_results("agent_negative_report", eval_result)
    reporter.save_results("raw_results", eval_input_list)

    print(f"  Agent 负向轨迹完成 {len(per_case_list)} 条")

