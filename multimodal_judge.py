import requests
import base64
import json
import os
import yaml
import time
from datetime import datetime
from dotenv import load_dotenv

# 1. 加载环境变量
load_dotenv()


def load_yaml(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# 2. 读取配置
MODELS_CFG = load_yaml("config/models.yaml")["models"]
DATASETS_CFG = load_yaml("config/datasets.yaml")["datasets"]

MODEL_NAME = "deepseek-vision"
DATASET_NAME = "multimodal-images"

model_cfg = MODELS_CFG[MODEL_NAME]
dataset_cfg = DATASETS_CFG[DATASET_NAME]

api_key = os.getenv(model_cfg["api_key_env"])
if not api_key:
    print(f"❌ 未找到环境变量 {model_cfg['api_key_env']}")
    exit(1)

# ========== 新增：创建独立的 results 归档目录 ==========
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
RUN_DIR = f"results/{ts}_multimodal-judge_{MODEL_NAME}_{DATASET_NAME}"
os.makedirs(RUN_DIR, exist_ok=True)
print(f"📁 结果将归档至: {RUN_DIR}")

# ========== 新增：保存配置快照 ==========
with open(os.path.join(RUN_DIR, "config_snapshot.json"), "w", encoding="utf-8") as f:
    json.dump({"model_config": model_cfg, "dataset_config": dataset_cfg}, f, indent=2)

# 3. 读取数据集
with open(dataset_cfg["path"], "r", encoding="utf-8") as f:
    test_cases = json.load(f)

JUDGE_PROMPT_TEMPLATE = """
你是一个严格的视觉质检员。请评估这张图片是否符合以下要求：
【要求】：{requirement}
【评判标准】：
{scoring}

请输出 JSON 格式：{{"score": 0-100, "reason": "扣分原因"}}
"""

all_results = []

# 5. 遍历数据集
for case in test_cases:
    image_path = case['image_path']
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        requirement=case["requirement"],
        scoring=case["scoring"]
    )

    print(f"🚀 正在评测 {case['id']} ({image_path})，使用模型 [{model_cfg['model']}]...")

    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"❌ 找不到图片 {image_path}")
        continue

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_cfg["model"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        "temperature": model_cfg.get("temperature", 0.1),
        "max_tokens": model_cfg.get("max_tokens", 500)
    }

    try:
        r = requests.post(model_cfg["url"], headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        raw_result = r.json()["choices"][0]["message"]["content"]

        # 解析 JSON
        judge_data = json.loads(raw_result)

        record = {
            "id": case["id"],
            "image_path": image_path,
            "requirement": case["requirement"],
            "score": judge_data.get("score"),
            "reason": judge_data.get("reason")
        }
        all_results.append(record)
        print(f"  ✅ 得分: {record['score']} | 理由: {record['reason'][:30]}...")

    except Exception as e:
        print(f"  ❌ 调用失败: {e}")

# ========== 新增：生成最终报告 ==========
report_path = os.path.join(RUN_DIR, "multimodal_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump({"total": len(all_results), "results": all_results}, f, indent=2, ensure_ascii=False)

print(f"\n✅ 评测完成，报告已保存至: {report_path}")