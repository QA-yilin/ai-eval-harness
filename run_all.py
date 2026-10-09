import subprocess

TASKS = [
    ("rag-layered", "deepseek", "golden-set-8"),
    ("judge-calibration", "deepseek", "judge-calibration-v1"),
    ("agent-trajectory", "deepseek", "agent-tasks"),
    ("prompt-injection", "deepseek", "injection-cases"),
]

for task, model, dataset in TASKS:
    print(f"\n{'='*60}")
    print(f"跑任务：{task}")
    print('='*60)
    subprocess.run([
        "python", "run.py",
        "--task", task,
        "--model", model,
        "--dataset", dataset,
    ])

print("\n全部任务完成。")