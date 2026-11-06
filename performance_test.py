# performance_test.py
import time
import requests
import os
import json
import threading
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# 并发数
CONCURRENCY = 5
PROMPT = "请写一段200字左右的关于人工智能发展历史的介绍。"


def measure_ttft():
    """测量单次请求的首字延迟 (TTFT) 和 总耗时"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0.1,
        "stream": True  # 必须开启流式输出才能测首字延迟
    }

    start_time = time.time()
    first_token_time = None
    total_tokens = 0

    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=payload, stream=True, timeout=60)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                if first_token_time is None:
                    first_token_time = time.time()
                # 简单的统计 token 数量（按 chunk 估算）
                total_tokens += 1

        end_time = time.time()
        ttft = (first_token_time - start_time) * 1000 if first_token_time else 0  # 毫秒
        total_time = (end_time - start_time) * 1000

        return {"ttft": ttft, "total_time": total_time, "status": "success"}
    except Exception as e:
        return {"ttft": 0, "total_time": 0, "status": f"error: {e}"}


def run_concurrency_test():
    results = []

    def worker():
        res = measure_ttft()
        results.append(res)
        print(f"  单次完成: TTFT={res['ttft']:.2f}ms, 总耗时={res['total_time']:.2f}ms")

    threads = []
    print(f"开始并发压测，并发数：{CONCURRENCY}")
    for _ in range(CONCURRENCY):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # 统计结果
    success_results = [r for r in results if r["status"] == "success"]
    if success_results:
        ttfts = sorted([r["ttft"] for r in success_results])
        p95_index = int(len(ttfts) * 0.95) - 1
        p95_ttft = ttfts[p95_index] if p95_index >= 0 else ttfts[-1]

        print("\n=== 压测报告 ===")
        print(f"总请求数: {len(results)}")
        print(f"成功率: {len(success_results) / len(results) * 100:.1f}%")
        print(f"平均 TTFT: {sum(ttfts) / len(ttfts):.2f} ms")
        print(f"P95 TTFT: {p95_ttft:.2f} ms (包含网络波动与排队延迟)")


if __name__ == "__main__":
    run_concurrency_test()