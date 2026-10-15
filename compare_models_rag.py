# -*- coding: utf-8 -*-
"""
RAG场景模型对比：DeepSeek vs Qwen2.5:14b
用法：python compare_models_rag.py [--ids Q6,Q15a,Q15b] [--repeat 3]
输出：rag_model_comparison.jsonl + rag_comparison_report.json
"""
import json
import time
import os
import sys
import re
import statistics
import requests
from dotenv import load_dotenv
load_dotenv()


# ========== 配置 ==========
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/generate"
QWEN_MODEL = "qwen2.5:14b"
GOLDEN_SET_PATH = "datasets/golden-set-18.json"
CORPUS_PATH = "datasets/corpus.json"

# ========== 参数解析 ==========
repeat = 1
if "--repeat" in sys.argv:
    idx = sys.argv.index("--repeat")
    repeat = int(sys.argv[idx + 1])

# ========== 输出目录 ==========
timestamp = time.strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = f"results/{timestamp}_rag-model-comparison_deepseek-vs-qwen_repeat{repeat}"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_PATH = f"{OUTPUT_DIR}/rag_model_comparison.jsonl"
REPORT_PATH = f"{OUTPUT_DIR}/rag_comparison_report.json"
print(f"输出目录: {OUTPUT_DIR}")
print(f"重复采样次数: {repeat}")

# ========== 加载 Golden Set ==========
with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
items = data["golden_set"]["items"] if "golden_set" in data else data

if "--ids" in sys.argv:
    idx = sys.argv.index("--ids")
    wanted = set(sys.argv[idx + 1].split(","))
    items = [it for it in items if it["id"] in wanted]
    print(f"筛选后 {len(items)} 道题: {[it['id'] for it in items]}")

print(f"加载 {len(items)} 道 RAG 题")

# ========== 加载 corpus ==========
with open(CORPUS_PATH, "r", encoding="utf-8") as f:
    corpus = json.load(f)
print(f"加载 {len(corpus)} 个文档片段")


# ========== 构建 RAG Prompt ==========
def build_rag_prompt(item):
    context_ids = item.get("gold_chunk_ids", [])
    contexts = [c["text"] for c in corpus if c["chunk_id"] in context_ids]
    context_str = "\n---\n".join(contexts)
    return f"""请基于以下公司制度文档回答问题。请完整回答，不要遗漏关键信息。如果文档中没有相关信息，请明确说明"文档中未提及"，不要编造，也不要基于常识推断。

【文档】
{context_str}

【问题】
{item['question']}
"""


# ========== 调用 DeepSeek ==========
def ask_deepseek(prompt, retries=3):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个企业知识库助手。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 800
    }
    for i in range(retries):
        try:
            r = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=120)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  DeepSeek 重试 {i+1}/{retries}: {e}")
            time.sleep(2 ** i)
    return None


# ========== 调用 Qwen ==========
def ask_qwen(prompt, retries=3):
    payload = {
        "model": QWEN_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.1, "seed": 42, "num_predict": 800}
    }
    for i in range(retries):
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=120)
            r.raise_for_status()
            return r.json()["response"]
        except Exception as e:
            print(f"  qwen 重试 {i+1}/{retries}: {e}")
            time.sleep(2 ** i)
    return None


# ========== Judge ==========
JUDGE_PROMPT = """你是一个严格的评测专家。请根据以下标准给模型回答打分。

【问题】
{question}

【标准答案】
{ground_truth}

【评分标准】
{scoring}

【模型回答】
{answer}

请严格按评分标准打分，输出 JSON：
{{"score": 0-100, "reason": "打分理由"}}

【打分要求】
1. 先逐项核对评分标准中的每个得分点，在 reason 中明确写出"得分点X：满足/不满足，得X分"。
2. 再核对 penalty 中的每个扣分项，在 reason 中明确写出"扣分项X：触发/未触发，扣X分"。
3. score 必须等于"所有得分点之和 - 所有扣分项之和"，且 score 必须在 0-100 之间。
4. reason 中必须包含最终计算式，格式如："总分 = 50 + 30 + 20 - 0 = 100"。
5. 如果 score 与 reason 中的计算式不一致，视为无效输出，必须重新计算。
6. 不要出现"可能""推断"等超出文档范围的表述，除非评分标准明确要求。
7. reason 控制在200字以内。
8. 只输出 JSON，不要输出任何其他内容。"""


def extract_calc_score(reason):
    m = re.search(r'=\s*(\d+)\s*$', reason.strip())
    if m:
        return int(m.group(1))
    return None


def judge_answer(question, ground_truth, scoring, answer, retries=3):
    prompt = JUDGE_PROMPT.format(
        question=question,
        ground_truth=ground_truth,
        scoring=scoring,
        answer=answer
    )
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"}
    }
    for i in range(retries):
        try:
            r = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=120)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]

            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                raw_fixed = raw.rstrip()
                if not raw_fixed.endswith("}"):
                    if raw_fixed.count('"') % 2 == 1:
                        raw_fixed += '"'
                    raw_fixed += "}"
                result = json.loads(raw_fixed)

            score = result.get("score")
            reason = result.get("reason", "")

            if not isinstance(score, (int, float)):
                print(f"  Judge 输出 score 非数字，重试 {i+1}/{retries}")
                continue
            if "=" not in reason:
                print(f"  Judge reason 缺少计算式，重试 {i+1}/{retries}")
                continue

            calc_score = extract_calc_score(reason)
            if calc_score is not None and calc_score != score:
                print(f"  Judge score={score} 与计算式={calc_score} 不一致，重试 {i+1}/{retries}")
                continue

            return result
        except Exception as e:
            print(f"  Judge 失败: {e}")
            print(f"  Raw output: {raw[:500] if 'raw' in locals() else 'N/A'}")
            time.sleep(1)
    return {"score": None, "reason": "Judge 重试后仍无效"}


# ========== 逐题对比 ==========
results = []
for i, item in enumerate(items):
    print(f"\n[{i+1}/{len(items)}] {item['id']} - {item['question'][:30]}...")
    prompt = build_rag_prompt(item)

    for r in range(repeat):
        ds_answer = ask_deepseek(prompt)
        ds_score = judge_answer(item["question"], item["gold_answer"], item["scoring"], ds_answer) if ds_answer else None

        qw_answer = ask_qwen(prompt)
        qw_score = judge_answer(item["question"], item["gold_answer"], item["scoring"], qw_answer) if qw_answer else None

        record = {
            "id": item["id"],
            "repeat": r,
            "question": item["question"],
            "category": item.get("query_type", item.get("category", "")),
            "difficulty": item.get("difficulty", ""),
            "deepseek_answer": ds_answer,
            "deepseek_score": ds_score["score"] if ds_score else None,
            "deepseek_reason": ds_score["reason"] if ds_score else None,
            "qwen_answer": qw_answer,
            "qwen_score": qw_score["score"] if qw_score else None,
            "qwen_reason": qw_score["reason"] if qw_score else None,
        }
        results.append(record)

        with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"  [repeat {r}] DeepSeek: {record['deepseek_score']}分 | qwen: {record['qwen_score']}分")


# ========== 汇总报告 ==========
by_id = {}
for r in results:
    by_id.setdefault(r["id"], {"ds": [], "qw": []})
    if r["deepseek_score"] is not None:
        by_id[r["id"]]["ds"].append(r["deepseek_score"])
    if r["qwen_score"] is not None:
        by_id[r["id"]]["qw"].append(r["qwen_score"])

detail = {}
for qid, scores in by_id.items():
    detail[qid] = {
        "deepseek": {
            "scores": scores["ds"],
            "mean": round(statistics.mean(scores["ds"]), 2) if scores["ds"] else None,
            "std": round(statistics.stdev(scores["ds"]), 2) if len(scores["ds"]) > 1 else 0,
            "range": max(scores["ds"]) - min(scores["ds"]) if scores["ds"] else None,
        },
        "qwen": {
            "scores": scores["qw"],
            "mean": round(statistics.mean(scores["qw"]), 2) if scores["qw"] else None,
            "std": round(statistics.stdev(scores["qw"]), 2) if len(scores["qw"]) > 1 else 0,
            "range": max(scores["qw"]) - min(scores["qw"]) if scores["qw"] else None,
        },
    }

ds_all = [r["deepseek_score"] for r in results if r["deepseek_score"] is not None]
qw_all = [r["qwen_score"] for r in results if r["qwen_score"] is not None]

report = {
    "total_questions": len(by_id),
    "repeat": repeat,
    "total_runs": len(results),
    "deepseek_avg": round(statistics.mean(ds_all), 2) if ds_all else 0,
    "qwen_avg": round(statistics.mean(qw_all), 2) if qw_all else 0,
    "gap": round(statistics.mean(ds_all) - statistics.mean(qw_all), 2) if ds_all and qw_all else 0,
    "detail": detail,
}

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n=== 对比结果 ===")
print(f"DeepSeek 均分: {report['deepseek_avg']}")
print(f"qwen2.5 均分: {report['qwen_avg']}")
print(f"差距: {report['gap']}")
print(f"\n=== 逐题方差 ===")
for qid, d in detail.items():
    print(f"{qid}: DS={d['deepseek']['scores']} (std={d['deepseek']['std']}) | QW={d['qwen']['scores']} (std={d['qwen']['std']})")