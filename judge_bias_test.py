# -*- coding: utf-8 -*-
"""
Judge位置偏差检测（自包含版）
先调模型生成回答，再对同一答案做位置偏差检测
"""
import json
import time
import os
import statistics
import requests
from dotenv import load_dotenv
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/generate"
QWEN_MODEL = "qwen2.5:14b"
GOLDEN_SET_PATH = "datasets/golden-set-19.json"
CORPUS_PATH = "datasets/corpus.json"

JUDGE_PROMPT_NORMAL = """你是一个严格的评测专家。请根据以下标准给模型回答打分。

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
1. 逐项核对得分点，reason中写明"得分点X：满足/不满足，得X分"。
2. score = 得分点之和 - 扣分项之和。
3. reason中必须包含计算式，格式"总分 = 50 + 30 + 20 - 0 = 100"。
4. reason控制在200字以内。
5. 只输出JSON。"""

JUDGE_PROMPT_SWAPPED = """你是一个严格的评测专家。请根据以下标准给模型回答打分。

【问题】
{question}

【模型回答】
{answer}

【标准答案】
{ground_truth}

【评分标准】
{scoring}

请严格按评分标准打分，输出 JSON：
{{"score": 0-100, "reason": "打分理由"}}

【打分要求】
1. 逐项核对得分点，reason中写明"得分点X：满足/不满足，得X分"。
2. score = 得分点之和 - 扣分项之和。
3. reason中必须包含计算式，格式"总分 = 50 + 30 + 20 - 0 = 100"。
4. reason控制在200字以内。
5. 只输出JSON。"""


def build_rag_prompt(item, corpus):
    context_ids = item.get("gold_chunk_ids", [])
    contexts = [c["text"] for c in corpus if c["chunk_id"] in context_ids]
    context_str = "\n---\n".join(contexts)
    return f"""请基于以下公司制度文档回答问题。如果文档中没有相关信息，请明确说明"文档中未提及"。

【文档】
{context_str}

【问题】
{item['question']}
"""


def ask_deepseek(prompt):
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
    for i in range(3):
        try:
            r = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=120)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  DeepSeek失败: {e}")
            time.sleep(2)
    return None


def ask_qwen(prompt):
    payload = {
        "model": QWEN_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.1, "seed": 42, "num_predict": 800}
    }
    for i in range(3):
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=120)
            r.raise_for_status()
            return r.json()["response"]
        except Exception as e:
            print(f"  Qwen失败: {e}")
            time.sleep(2)
    return None


def call_judge(prompt):
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
    for i in range(3):
        try:
            r = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=120)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                raw_fixed = raw.rstrip()
                if not raw_fixed.endswith("}"):
                    if raw_fixed.count('"') % 2 == 1:
                        raw_fixed += '"'
                    raw_fixed += "}"
                return json.loads(raw_fixed)
        except Exception as e:
            print(f"  Judge失败: {e}")
            time.sleep(1)
    return {"score": None, "reason": "失败"}


def main():
    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data["golden_set"]["items"] if "golden_set" in data else data

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    target_ids = ["Q6", "Q15a", "Q15b", "Q16", "Q18"]
    items = [it for it in items if it["id"] in target_ids]

    print(f"共 {len(items)} 题\n")

    results = []
    for item in items:
        qid = item["id"]
        print(f"[{qid}]")
        prompt = build_rag_prompt(item, corpus)

        ds_answer = ask_deepseek(prompt)
        if ds_answer:
            print(f"  DeepSeek回答长度: {len(ds_answer)}")
            r_n = call_judge(JUDGE_PROMPT_NORMAL.format(
                question=item["question"], ground_truth=item["gold_answer"],
                scoring=item["scoring"], answer=ds_answer))
            r_s = call_judge(JUDGE_PROMPT_SWAPPED.format(
                question=item["question"], ground_truth=item["gold_answer"],
                scoring=item["scoring"], answer=ds_answer))
            sn, ss = r_n.get("score"), r_s.get("score")
            diff = (sn - ss) if sn is not None and ss is not None else None
            print(f"  DeepSeek: 原={sn} 交换={ss} 差值={diff}")
            results.append({"id": qid, "model": "deepseek", "score_normal": sn,
                            "score_swapped": ss, "diff": diff})

        qw_answer = ask_qwen(prompt)
        if qw_answer:
            print(f"  Qwen回答长度: {len(qw_answer)}")
            r_n = call_judge(JUDGE_PROMPT_NORMAL.format(
                question=item["question"], ground_truth=item["gold_answer"],
                scoring=item["scoring"], answer=qw_answer))
            r_s = call_judge(JUDGE_PROMPT_SWAPPED.format(
                question=item["question"], ground_truth=item["gold_answer"],
                scoring=item["scoring"], answer=qw_answer))
            sn, ss = r_n.get("score"), r_s.get("score")
            diff = (sn - ss) if sn is not None and ss is not None else None
            print(f"  Qwen: 原={sn} 交换={ss} 差值={diff}")
            results.append({"id": qid, "model": "qwen", "score_normal": sn,
                            "score_swapped": ss, "diff": diff})

    diffs = [r["diff"] for r in results if r["diff"] is not None]
    report = {
        "total": len(results),
        "mean_diff": round(statistics.mean(diffs), 2) if diffs else 0,
        "abs_mean_diff": round(statistics.mean([abs(d) for d in diffs]), 2) if diffs else 0,
        "max_diff": max(diffs) if diffs else 0,
        "min_diff": min(diffs) if diffs else 0,
        "details": results,
    }

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR = f"results/{timestamp}_judge-bias_deepseek-vs-qwen"

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(f"{OUTPUT_DIR}/judge_bias_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n报告已保存：{OUTPUT_DIR}/judge_bias_report.json")
    print(f"\n=== 汇总 ===")

    print(f"\n=== 汇总 ===")
    print(f"样本数: {report['total']}")
    print(f"平均差值: {report['mean_diff']}")
    print(f"平均绝对差值: {report['abs_mean_diff']}")
    print(f"最大差值: {report['max_diff']}")
    print(f"最小差值: {report['min_diff']}")


if __name__ == "__main__":
    main()