# RAG 分层评测报告

## 分层结果

| id | 检索层 | 理解层 | 生成层 | first_failing |
|----|--------|--------|--------|---------------|
| Q1 | FAIL | PASS | FAIL | retrieval_layer |
| Q2 | FAIL | FAIL | FAIL | retrieval_layer |
| Q3 | PASS | PASS | PASS | none |
| Q4 | FAIL | FAIL | FAIL | retrieval_layer |
| Q5 | FAIL | PASS | FAIL | retrieval_layer |
| Q6 | FAIL | FAIL | FAIL | retrieval_layer |
| Q7 | SKIP | SKIP | PASS | none |
| Q8 | FAIL | FAIL | FAIL | retrieval_layer |

## first_failing_layer 分布

- retrieval_layer: 6
- none: 2