# pytest 架构迁移到 AI 评测 Harness

## 核心观点

**Harness = pytest 的 AI 评测版。**

配置层、用例层、执行层、适配层、报告层全部同构。
唯一核心差异：断言层从 `assert` 换成 `evaluator`（多维指标 + 阈值 + 分层判定）。

10 年 pytest 经验，90% 直接迁移。

---

## 一、整体架构对照

| 层 | pytest | Harness |
|----|--------|---------|
| 配置层 | pytest.ini / conftest.py | config/*.yaml |
| 用例层 | test_*.py | tasks/*.py |
| 执行层 | pytest runner | core/runner.py |
| 断言层 | assert | core/evaluator.py |
| 报告层 | pytest-html / allure | core/reporter.py |
| 数据层 | testdata/ | datasets/ |
| 适配层 | Page Object | adapters/ |

---

## 二、逐模块对照

### 2.1 配置层

| pytest | Harness | 作用 |
|--------|---------|------|
| pytest.ini | config/tasks.yaml | 声明任务 |
| conftest.py | config/models.yaml | 共享 fixture / 模型配置 |
| --env=staging | --model deepseek | 运行时切换环境 |
| pytest.mark.smoke | task: rag-layered | 任务标记 |

**核心相同**：配置和代码分离，运行时切换。

### 2.2 用例层

| pytest | Harness |
|--------|---------|
| def test_login(): | def run_rag_task(...): |
| @pytest.mark.parametrize | for item in golden: |
| fixture 注入依赖 | executor / evaluator 注入 |
| assert result == expected | evaluator.evaluate("retrieval", results) |

**核心区别**：

- pytest 断言是二元（通过/失败）
- Harness 评测是多维（Recall/Noise/Faithfulness/Kappa）

**这就是 LLM 测试和传统测试的本质差异**：断言写不死，要算指标。

### 2.3 执行层

| pytest | Harness |
|--------|---------|
| pytest runner | core/runner.py |
| test session | Runner.run() |
| test collection | tasks.yaml 加载 |
| fixture setup/teardown | Reporter.__init__ 建 run 目录 |

**核心相同**：调度器负责收集任务、执行、汇总。

### 2.4 断言层（最大差异）

| pytest | Harness |
|--------|---------|
| assert a == b | _eval_retrieval / _eval_generation |
| assertTrue/assertEqual | recall_at_k / faithfulness |
| 二元通过/失败 | 多维指标 + 阈值判定 |
| 失败即抛异常 | 失败记 FAIL，继续跑 |

**LLM 评测的核心特殊性**：

- 传统测试：一个断言失败 = 用例失败
- LLM 评测：一个指标不达标 = 该层 FAIL，但其他层可能 PASS
- 分层诊断 = 断言层拆成三层，分别判定

### 2.5 报告层

| pytest | Harness |
|--------|---------|
| pytest-html 报告 | report.md |
| junit.xml | *.json 结构化结果 |
| 通过率/失败列表 | Kappa / MAE / first_failing_layer |
| 单次运行报告 | 独立 run 目录 + 配置快照 |

**Harness 更强的地方**：每次运行独立目录 + 配置快照，可复现性比 pytest 好。

### 2.6 数据层

| pytest | Harness |
|--------|---------|
| testdata/login.json | datasets/golden-set-8.json |
| @pytest.fixture(params=...) | for item in golden: |
| csv/xlsx 数据驱动 | jsonl 结果驱动 |

**核心相同**：数据驱动。

### 2.7 适配层

| pytest | Harness |
|--------|---------|
| Page Object（Selenium） | ModelAdapter（DeepSeek/Ollama） |
| API Client（requests） | RetrieverAdapter |
| DB Helper | JudgeAdapter |

**核心相同**：外部依赖隔离。UI 变了改 Page Object，模型换了改 Adapter。

---

## 三、三个关键差异

### 差异 1：断言的确定性

| | pytest | Harness |
|---|--------|---------|
| 输入 | 确定 | 概率性 |
| 输出 | 确定 | 概率性 |
| 断言 | == | 阈值 + 指标 |
| 复现 | 必现 | 需多次采样 |

**Harness 的核心难点**：结果不确定，必须用统计指标 + 分层判定。

### 差异 2：评测者本身也要校准

| pytest | Harness |
|--------|---------|
| 断言是确定性的 | Judge 是概率性的 |
| 不用校准断言 | 必须校准 Judge |

**这是 LLM 评测独有的**：评测工具本身也是被测对象。

### 差异 3：分层诊断

| pytest | Harness |
|--------|---------|
| 用例失败 = 二元 | 分层判定 + first_failing_layer |
| 定位到具体断言 | 定位到具体层 |

**这是 RAG 评测的核心方法**：从最靠前的 FAIL 层开始排查。

---

## 四、直接可复用的 pytest 经验

| pytest 经验 | Harness 对应 |
|-------------|-------------|
| 分层测试（单元/集成/系统） | 分层评测（检索/理解/生成） |
| Page Object 隔离 UI | Adapter 隔离模型 |
| fixture 管理依赖 | Runner 管理 executor |
| conftest 共享配置 | config/*.yaml |
| 数据驱动 | golden set |
| 断言库扩展 | evaluator 扩展 |
| 测试工具本身要验证 | Judge 校准 |
| CI 集成 | run.py 接 CI |
| Allure 报告 | Reporter + Markdown |

**90% 直接迁移。**

---

## 五、面试话术

> "Harness 的架构和我以前写的 pytest 框架是同构的。**配置层**对应 pytest.ini/conftest，**用例层**对应 test_*.py，**执行层**对应 pytest runner，**适配层**对应 Page Object，**报告层**对应 Allure。核心区别在**断言层**——pytest 用 assert 判二元对错，Harness 用 evaluator 算多维指标，因为 LLM 输出不确定。另一个独有差异是 **Judge 本身也要校准**，这是传统测试没有的——测试工具本身也要被测。"

**这段回答体现**：

1. 能把 AI 评测映射到熟悉的测试框架
2. 知道两者的本质差异
3. 不是从零学 AI 评测，是迁移已有能力

---

## 六、一句话

**Harness = pytest 的 AI 评测版。配置层、用例层、执行层、适配层、报告层全部同构，只有断言层从 assert 换成 evaluator（多维指标 + 阈值 + 分层判定）。10 年 pytest 经验，90% 直接迁移。独有差异只有两个：结果不确定要统计，Judge 本身也要校准。**