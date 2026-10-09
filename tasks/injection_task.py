import json


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_multi_turn(rounds, system_prompt, executor):
    final_answer = ""
    for r in rounds:
        prompt = f"{system_prompt}\n\n用户：{r}"
        final_answer = executor.call_model(prompt)
    return final_answer


def run_injection_task(task_cfg, executor, evaluator, reporter, dataset_cfg):
    data = load_json(dataset_cfg["path"])
    system_prompt = data["system_prompt"]
    cases = data["cases"]
    results = []
    for c in cases:
        print(f"[{c['id']}] {c['method']}")
        if "rounds" in c:
            answer = run_multi_turn(c["rounds"], system_prompt, executor)
        elif "tool_return" in c:
            prompt = f"工具返回：{c['tool_return']}\n请根据以上信息回答用户。"
            answer = executor.call_model(prompt, system_prompt=system_prompt)
        else:
            answer = executor.call_model(c["input"], system_prompt=system_prompt)
        check = evaluator.evaluate("injection_defense", {"answer": answer})
        results.append({"id": c["id"], "method": c["method"], "answer": answer, "check": check})
    reporter.save_results("raw_results", results)

    total = len(results)
    defended = sum(1 for r in results if r["check"]["defended"])
    summary = {"total": total, "defended": defended, "rate": defended / total if total else 0}
    reporter.save_results("injection_summary", summary)
    print(f"  防御成功率：{defended}/{total} = {summary['rate']:.1%}")