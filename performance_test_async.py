# performance_test_async.py
import asyncio
import aiohttp
import os
import json
import time
import statistics
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# 配置
MAX_CONCURRENCY = 100   # Semaphore最大并发限流
TOTAL_REQUEST = 100     # 总请求数量
PROMPT = "请写一段200字左右的关于人工智能发展历史的介绍。"
REQUEST_TIMEOUT = 60


async def measure_ttft(session: aiohttp.ClientSession, sem: asyncio.Semaphore):
    """异步测量单次流式请求 TTFT(ms)、总耗时，使用semaphore控制并发"""
    async with sem:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": PROMPT}],
            "temperature": 0.1,
            "stream": True
        }

        start_time = asyncio.get_event_loop().time()
        first_token_time = None
        status = "success"

        try:
            async with session.post(
                DEEPSEEK_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    return {
                        "ttft": 0,
                        "total_time": 0,
                        "status": f"http_error_{resp.status}: {text[:200]}"
                    }

                # 迭代流式chunk
                async for line in resp.content:
                    line = line.strip()
                    if not line:
                        continue
                    if first_token_time is None:
                        first_token_time = asyncio.get_event_loop().time()

            end_time = asyncio.get_event_loop().time()
            ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else 0
            total_ms = (end_time - start_time) * 1000
            return {
                "ttft": round(ttft_ms, 2),
                "total_time": round(total_ms, 2),
                "status": status
            }

        except Exception as e:
            return {
                "ttft": 0,
                "total_time": 0,
                "status": f"exception: {str(e)}"
            }


async def run_concurrency_test():
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [measure_ttft(session, sem) for _ in range(TOTAL_REQUEST)]
        print(f"开始异步压测，总请求数:{TOTAL_REQUEST}, 最大并发Semaphore:{MAX_CONCURRENCY}")
        raw_results = await asyncio.gather(*tasks)

    results = raw_results
    success_list = [r for r in results if r["status"] == "success"]
    error_list = [r for r in results if r["status"] != "success"]
    total_cnt = len(results)
    success_cnt = len(success_list)
    error_cnt = len(error_list)
    success_rate = round(success_cnt / total_cnt * 100, 2) if total_cnt > 0 else 0

    report = {
        "total": total_cnt,
        "max_concurrency": MAX_CONCURRENCY,
        "success_count": success_cnt,
        "error_count": error_cnt,
        "success_rate": success_rate,
        "ttft_stats": {},
        "total_time_stats": {},
        "details": results
    }

    if success_list:
        ttfts = [item["ttft"] for item in success_list]
        total_times = [item["total_time"] for item in success_list]

        def percentile(sorted_list, pct):
            lst = sorted(sorted_list)
            idx = int(len(lst) * pct)
            idx = min(idx, len(lst)-1)
            return round(lst[idx], 2)

        report["ttft_stats"] = {
            "mean": round(statistics.mean(ttfts), 2),
            "p50": percentile(ttfts, 0.50),
            "p90": percentile(ttfts, 0.90),
            "p95": percentile(ttfts, 0.95),
            "p99": percentile(ttfts, 0.99),
            "max": round(max(ttfts), 2),
            "min": round(min(ttfts), 2)
        }
        report["total_time_stats"] = {
            "mean": round(statistics.mean(total_times),2),
            "p50": percentile(total_times,0.50),
            "p95": percentile(total_times,0.95),
            "max": round(max(total_times),2),
            "min": round(min(total_times),2)
        }

    # 保存报告，完全仿照你给的文件输出格式
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR = f"results/{timestamp}_perf_deepseek_async"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = f"{OUTPUT_DIR}/perf_test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n报告已保存：{report_path}")
    print(f"\n=== 汇总 ===")
    print(f"总请求数: {report['total']}")
    print(f"最大并发设置: {report['max_concurrency']}")
    print(f"成功数: {report['success_count']}")
    print(f"失败数: {report['error_count']}")
    print(f"成功率: {report['success_rate']}%")

    if success_list:
        print("\n--- TTFT首字延迟(ms) ---")
        s = report.get("ttft_stats", {})
        print(f"平均TTFT: {s.get('mean', 0)}")
        print(f"P50 TTFT: {s.get('p50', 0)}")
        print(f"P90 TTFT: {s.get('p90', 0)}")
        print(f"P95 TTFT: {s.get('p95', 0)}")
        print(f"P99 TTFT: {s.get('p99', 0)}")
        print(f"最大TTFT: {s.get('max', 0)}")
        print(f"最小TTFT: {s.get('min', 0)}")

        print("\n--- 请求总耗时(ms) ---")
        t = report.get("total_time_stats", {})
        print(f"平均总耗时: {t.get('mean', 0)}")
        print(f"P50总耗时: {t.get('p50', 0)}")
        print(f"P95总耗时: {t.get('p95', 0)}")
        print(f"最大总耗时: {t.get('max', 0)}")
        print(f"最小总耗时: {t.get('min', 0)}")

    if error_list:
        print(f"\n错误样例(最多展示5条):")
        for e in error_list[:5]:
            print(f"  {e.get('status', 'unknown')}")


if __name__ == "__main__":
    asyncio.run(run_concurrency_test())
