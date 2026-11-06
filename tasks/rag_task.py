import json
import re
import math
from collections import Counter

RAG_PROMPT = """基于以下上下文回答问题，不要编造上下文之外的信息。
如果上下文中没有答案，请回答"上下文中未找到相关信息"。

上下文：
{context}

问题：{question}
"""


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_ngrams(text, n=2):
    """提取字符级 n-gram（中文极快且效果不错的替代方案）"""
    text = re.sub(r'\s+', '', text)
    return [text[i:i + n] for i in range(len(text) - n + 1)] + list(text)


def calculate_tf_idf(query, docs):
    """纯 Python 实现轻量级 TF-IDF 向量检索"""
    query_grams = get_ngrams(query)
    doc_grams = [get_ngrams(d["text"]) for d in docs]

    # 计算 IDF
    N = len(docs)
    df = Counter()
    for grams in doc_grams:
        for gram in set(grams):
            df[gram] += 1
    idf = {gram: math.log(N / (1 + df[gram])) for gram in df}

    # 计算查询向量
    query_vec = Counter(query_grams)
    for gram in query_vec:
        query_vec[gram] *= idf.get(gram, 0)

    scored_docs = []
    for i, doc in enumerate(docs):
        doc_vec = Counter(doc_grams[i])
        for gram in doc_vec:
            doc_vec[gram] *= idf.get(gram, 0)

        # 余弦相似度
        intersection = set(query_vec.keys()) & set(doc_vec.keys())
        numerator = sum([query_vec[x] * doc_vec[x] for x in intersection])
        sum1 = sum([query_vec[x] ** 2 for x in query_vec.keys()])
        sum2 = sum([doc_vec[x] ** 2 for x in doc_vec.keys()])
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        cosine = numerator / denominator if denominator else 0.0
        scored_docs.append({**doc, "score": cosine})

    scored_docs.sort(key=lambda x: x["score"], reverse=True)
    return scored_docs

def simple_retriever(query, corpus, k=5):
    """使用 TF-IDF 向量检索替代简单的字符串包含"""
    return calculate_tf_idf(query, corpus)[:k]

def split_claims(answer):
    if not answer:
        return []
    parts = re.split(r"[。\n；;]", answer)
    stop = {"不可以", "可以", "是的", "不是", "不会", "会",
            "不免责", "免责", "因此", "所以", "综上", "总之"}
    return [p.strip() for p in parts if len(p.strip()) > 2 and p.strip() not in stop]


def run_rag_task(task_cfg, executor, evaluator, reporter, dataset_cfg):
    golden = load_json(dataset_cfg["path"])["golden_set"]["items"]
    corpus = load_json("datasets/corpus.json")

    results = []
    for item in golden:
        print(f"[{item['id']}] {item['question']}")
        retrieved = simple_retriever(item["question"], corpus, k=5)
        reranked = sorted(retrieved, key=lambda x: x["score"], reverse=True)[:3]
        context = "\n".join(d["text"] for d in reranked)
        prompt = RAG_PROMPT.format(context=context, question=item["question"])
        answer = executor.call_model(prompt)

        record = {
            "id": item["id"],
            "question": item["question"],
            "query_type": item.get("query_type"),
            "gold_chunk_ids": item.get("gold_chunk_ids", []),
            "gold_claims": item.get("gold_claims", []),
            "has_answer": item.get("has_answer", True),
            "retrieved_doc_ids": [d["chunk_id"] for d in retrieved],
            "reranked_doc_ids": [d["chunk_id"] for d in reranked],
            "selected_context_ids": [d["chunk_id"] for d in reranked],
            "context_text": context,
            "model_answer": answer,
            "claims": split_claims(answer),
        }
        results.append(record)

    reports = {}
    for evaluator_name in task_cfg["evaluators"]:
        report = evaluator.evaluate(evaluator_name, results)
        reports[evaluator_name] = report
        reporter.save_results(f"{evaluator_name}_report", report)
        print(f"  [{evaluator_name}] 完成")

    summary = summarize_layers(reports)
    reporter.save_results("layer_summary", summary)
    md = build_markdown(reports, summary)
    reporter.save_markdown("report", md)
    reporter.save_results("raw_results", results)


def summarize_layers(reports):
    r_map = {x["id"]: x for x in reports.get("retrieval", {}).get("per_case", [])}
    u_map = {x["id"]: x for x in reports.get("understanding", {}).get("per_case", [])}
    g_map = {x["id"]: x for x in reports.get("generation", {}).get("per_case", [])}

    rows = []
    for qid in sorted(set(r_map) | set(u_map) | set(g_map)):
        r = r_map.get(qid, {"status": "SKIP"})
        u = u_map.get(qid, {"status": "SKIP"})
        g = g_map.get(qid, {"status": "SKIP"})
        ff = "retrieval_layer" if r["status"] == "FAIL" else (
             "understanding_layer" if u["status"] == "FAIL" else (
             "generation_layer" if g["status"] == "FAIL" else "none"))
        rows.append({
            "id": qid, "retrieval": r["status"], "understanding": u["status"],
            "generation": g["status"], "first_failing_layer": ff,
        })
    dist = Counter(r["first_failing_layer"] for r in rows)
    return {"per_case": rows, "first_failing_distribution": dict(dist)}


def build_markdown(reports, summary):
    md = ["# RAG 分层评测报告\n"]
    md.append("## 分层结果\n")
    md.append("| id | 检索层 | 理解层 | 生成层 | first_failing |")
    md.append("|----|--------|--------|--------|---------------|")
    for r in summary["per_case"]:
        md.append(f"| {r['id']} | {r['retrieval']} | {r['understanding']} | {r['generation']} | {r['first_failing_layer']} |")
    md.append("\n## first_failing_layer 分布\n")
    for k, v in summary["first_failing_distribution"].items():
        md.append(f"- {k}: {v}")
    return "\n".join(md)