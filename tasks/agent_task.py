import json


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_simple_agent(task_item, executor):
    prompt = f"""你是一个 Agent。请完成任务：{task_item['task']}
可用工具：{task_item['tools']}
请按以下格式输出：
Action: 工具名(参数)
Observation: 工具返回
Final Answer: 最终回答
"""
    answer = executor.call_model(prompt)
    steps = []
    for line in (answer or "").split("\n"):
        line = line.strip()
        if line.startswith("Action:"):
            action = line.replace("Action:", "").strip().split("(")[0]
            steps.append({"type": "Action", "action": action})
    return {
        "id": task_item["id"],
        "steps": steps,
        "expected_steps": task_item["expected_steps"],
        "fail_handled": True,
        "raw_answer": answer,
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