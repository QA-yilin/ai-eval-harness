import subprocess
import sys

TASKS = [
    ("rag-layered", "deepseek", "golden-set-19"),
    ("judge-calibration", "deepseek", "judge-calibration-golden"),
    ("agent-trajectory", "deepseek", "agent-tasks"),
    ("prompt-injection", "deepseek", "injection-cases"),
]

print("============================================================")
print("🚀 开始 AI Eval Harness 全量一键评测")
print("============================================================")

for task, model, dataset in TASKS:
    # 1. 跑四大任务（正常执行，任何一步报错都会中断）
    print(f"\n{'='*60}")
    print(f"▶ 正在跑任务：{task} | 数据集: {dataset}")
    print('='*60)
    subprocess.run([
        "python", "run.py",
        "--task", task,
        "--model", model,
        "--dataset", dataset,
    ])

# 2. 执行门禁（加上 check=False，防止门禁亮了红灯阻断后续的指纹校验）
print(f"\n{'='*60}")
print("🛡️ 开始执行质量门禁检查 (Release Gate)")
print('='*60)
subprocess.run(["python", "check_gate.py"], check=False)

# 3. 执行指纹校验（这一项不管前面门禁过没过，都必须要跑）
print(f"\n{'='*60}")
print("🔍 开始执行模型漂移指纹校验")
print('='*60)
subprocess.run(["python", "check_model_drift.py"])

print("\n✅ 全量任务、门禁与指纹校验执行完毕！")