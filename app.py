import streamlit as st
import json
import os
import yaml
import plotly.express as px
import pandas as pd
from core.executor import Executor
from dotenv import load_dotenv
load_dotenv()

# ================= 页面基础配置 =================
st.set_page_config(page_title="AI 工程效能与质量门禁平台", page_icon="🛡️", layout="wide")
st.title("🛡️ AI 工程效能与质量门禁平台 (Harness V2.0)")
st.markdown("---")

# ================= 依赖注入：初始化底层执行引擎Executor =================
# 使用单例缓存防止 Streamlit 热更新导致重复实例化，消耗 API 额度
@st.cache_resource
def get_executor():
    try:
        with open("config/models.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)["models"]["deepseek"]
        return Executor(cfg)
    except Exception as e:
        st.error(f"加载模型配置失败: {e}")
        return None


executor = get_executor()

# ================= 页面 Tab 划分 =================
tab1, tab2, tab3 = st.tabs(["📊 质量看板 (RAG诊断)", "🤖 Agent 轨迹回放", "🔍 AI 代码变更审查"])

# ================= Tab 1: 质量看板 =================
with tab1:
    st.subheader("RAG 分层诊断首错归因")
    st.markdown("读取 `results` 目录下最新跑批的 `layer_summary.json`，直观展现检索层、理解层、生成层的失败分布。")

    # 这里为了方便演示，如果没读到本地文件，就用 Mock 数据
    # 你的真实环境中可以改成: with open("results/xxx/layer_summary.json") as f: ...
    mock_dist = {"none": 9, "retrieval_layer": 2, "understanding_layer": 2, "generation_layer": 6}

    df_dist = pd.DataFrame(list(mock_dist.items()), columns=["失败层级", "数量"])

    # 画柱状图
    fig = px.bar(df_dist, x="失败层级", y="数量", color="失败层级",
                 title="First Failing Layer 分布",
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig, use_container_width=True)

# ================= Tab 2: Agent 轨迹回放 =================
with tab2:
    st.subheader("Agent 死循环与异常恢复分析")
    st.markdown("读取 `agent_report.json`，回放 Thought -> Action -> Observation 全过程，自动高亮异常。")

    # 模拟一个死循环的 Trace 数据
    st.info("【当前正在回放】Case: A3 (纽约查天气超时死循环)")

    mock_trace = [
        {"step": 1, "type": "Thought", "content": "用户要查纽约天气，我调用 get_weather"},
        {"step": 2, "type": "Action", "content": "get_weather(city='纽约')"},
        {"step": 3, "type": "Observation", "content": "Error: 未找到城市 '纽约' 的天气数据"},
        {"step": 4, "type": "Thought", "content": "报错了，我再试一次，可能参数不对"},
        {"step": 5, "type": "Action", "content": "get_weather(city='纽约')"},
        {"step": 6, "type": "Observation", "content": "Error: 未找到城市 '纽约' 的天气数据"},
        {"step": 7, "type": "Action", "content": "get_weather(city='纽约')"},
        {"step": 8, "type": "Observation", "content": "Error: 未找到城市 '纽约' 的天气数据"}
    ]

    for t in mock_trace:
        if t["type"] == "Thought":
            st.write(f"🤔 **Thought**: {t['content']}")
        elif t["type"] == "Action":
            st.code(f"Action: {t['content']}", language="python")
        elif t["type"] == "Observation":
            if "Error" in t["content"]:
                st.error(f"⚠️ Observation: {t['content']}")
            else:
                st.success(f"✅ Observation: {t['content']}")

    st.warning("🛑 **【门禁判定结果】: FAIL** - 触发 `infinite_loop` 规则，已强制熔断！")

# ================= Tab 3: AI 代码变更审查 (重中之重) =================
with tab3:
    st.subheader("AI 代码审查与安全门禁 (AI Code Review)")
    st.markdown("模拟研发提交的 PR 代码。AI 会自动审查漏洞，**强制引用原代码行作为证据**，并触发拦截。")

    bad_code = """def get_user_info(username):
    # 漏洞1：硬编码敏感密码
    db_password = "admin123456" 

    # 漏洞2：SQL 注入风险（直接拼接字符串）
    sql = "SELECT * FROM users WHERE username = '" + username + "'"

    cursor.execute(sql)
    return cursor.fetchall()
"""

    st.code(bad_code, language="python")

    if st.button("🚀 执行 AI 代码审查", type="primary"):
        if not executor:
            st.error("大模型未初始化，请检查 .env 中的 API Key")
        else:
            with st.spinner("大模型正在逐行审查代码..."):
                prompt = f"""你是一个资深的代码安全审计专家。
请审查以下代码。如果发现漏洞（如SQL注入、硬编码密码），请必须给出严重等级（高危/低危），并引用原代码的行号作为证据。

【待审查代码】
{bad_code}

请严格输出 JSON 格式：
{{"status": "FAIL", "vulnerabilities": [{{"line": "行号", "type": "漏洞类型", "evidence": "原代码片段", "reason": "原因"}}]}}
只输出 JSON，不要其他废话。
"""
                # ================= 核心路由：调用底层 LLM 网关执行审查 =================
                # 此处复用 AI Eval Harness 的 Executor 核心模块，自动继承 AOP 拦截与流式熔断能力
                response = executor.call_model(prompt)

                try:
                    # 解析 JSON
                    json_str = response[response.find("{"):response.rfind("}") + 1]
                    result = json.loads(json_str)

                    st.error(f"❌ [发布门禁阻断] AI 审查未通过！")
                    for vul in result.get("vulnerabilities", []):
                        st.markdown(f"**行号**: `{vul.get('line')}` | **漏洞类型**: `{vul.get('type')}`")
                        st.code(vul.get('evidence'), language="python")
                        st.write(f"原因: {vul.get('reason')}")
                except Exception as e:
                    st.write("解析失败，原始输出如下：")
                    st.write(response)