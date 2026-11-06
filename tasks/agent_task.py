# tasks/agent_task.py
import json
import re
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
        "请严格按照以下格式输出：\n"
        "Thought: 思考过程\n"
        "Action: 工具名({参数JSON})\n"
        "（等待系统返回 Observation）\n"
        "...循环...\n"
        "Final Answer: 最终回答"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_item["task"]}
    ]

    steps = []

    for turn in range(max_turns):
        response = executor.call_model(messages)
        if not response:
            break

        if "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
            # 关键修改：把 Final Answer 映射为 reply，以对齐 expected_steps
            steps.append({"type": "Action", "tool": "reply", "args": {"content": final_answer}, "observation": "END"})
            break

        tool_name, tool_args = parse_action(response)
        if not tool_name:
            messages.append({"role": "assistant", "content": response})
            messages.append(
                {"role": "user", "content": "Observation: 格式错误。必须使用 Action: tool_name({args}) 的格式。"})
            steps.append({"type": "FormatError", "raw": response})
            continue

        observation = ToolRegistry.execute(tool_name, tool_args)

        steps.append({
            "type": "Action",
            "tool": tool_name,
            "args": tool_args,
            "observation": observation
        })

        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": f"Observation: {observation}"})

    return {
        "id": task_item["id"],
        "steps": steps,
        "expected_steps": task_item.get("expected_steps", []),
        "raw_answer": response if 'response' in locals() else ""
    }


def run_agent_task(task_cfg, executor, evaluator, reporter, dataset_cfg):
    tasks = load_json(dataset_cfg["path"])["tasks"]
    results = []
    for t in tasks:
        print(f"[{t['id']}] {t['task']}")
        trajectory = run_simple_agent(t, executor)
        check = evaluator.evaluate("agent_trajectory", trajectory)
        results.append({"id": t["id"], "trajectory": trajectory, "check": check})
    reporter.save_results("raw_results", results)
    reporter.save_results("agent_report", results)
    print(f"  Agent 轨迹完成 {len(results)} 条")