# check_model_drift.py
import os
import hashlib
import json
import requests
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# 定义一个绝对确定的极简 Prompt 作为探针
PROBE_PROMPT = "请只回答数字：1 + 1 等于几？"
BASELINE_FILE = "datasets/model_fingerprint_baseline.json"


def get_model_hash():
    """调用模型，返回极简回答的 MD5 哈希"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": PROBE_PROMPT}],
        "temperature": 0.0,  # 必须是 0，保证确定性
        "max_tokens": 10
    }

    r = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    answer = r.json()["choices"][0]["message"]["content"].strip()

    # 计算文本哈希
    text_hash = hashlib.md5(answer.encode('utf-8')).hexdigest()
    return answer, text_hash


def check_drift():
    print("🔍 开始模型漂移检测（指纹断言）...")
    answer, current_hash = get_model_hash()
    print(f"  模型回答: {answer}")
    print(f"  当前哈希: {current_hash}")

    # 如果基线文件存在，则对比
    if os.path.exists(BASELINE_FILE):
        with open(BASELINE_FILE, "r", encoding="utf-8") as f:
            baseline_data = json.load(f)

        baseline_hash = baseline_data.get("hash")
        baseline_model = baseline_data.get("model_name", "Unknown")

        if baseline_hash != current_hash:
            print(f"\n❌ [模型漂移告警] 哈希值与基线不匹配！")
            print(f"  基线模型: {baseline_model}")
            print(f"  基线哈希: {baseline_hash}")
            print(f"  当前哈希: {current_hash}")
            print("  推断：开发可能偷偷改了参数、换了底座模型，或者平台方做了静默更新！")
        else:
            print(f"\n✅ [检测通过] 当前模型指纹与基线一致。")
    else:
        # 如果基线不存在，则生成基线
        baseline_data = {
            "model_name": "deepseek-chat",
            "temperature": 0.0,
            "probe_prompt": PROBE_PROMPT,
            "expected_answer": answer,
            "hash": current_hash
        }
        with open(BASELINE_FILE, "w", encoding="utf-8") as f:
            json.dump(baseline_data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 首次运行，已生成基线文件：{BASELINE_FILE}")


if __name__ == "__main__":
    check_drift()