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


# ================= 初始化 Executor =================
@st.cache_resource
def get_executor():
    try:
        with open("config/models.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)["models"]["deepseek"]
        return Executor(cfg)
    except Exception as e:
        return None


executor = get_executor()


# ================= 辅助函数：读取最新结果 =================
def get_latest_run_dir(prefix):
    """去 results 目录下找带有特定前缀的最新文件夹"""
    results_dir = "results"
    if not os.path.exists(results_dir):
        return None

    # 找出所有符合前缀的文件夹
    dirs = [d for d in os.listdir(results_dir) if d.startswith(prefix) or prefix in d]
    if not dirs:
        return None
    # 按名字排序（因为名字里有时间戳），取最新的
    dirs.sort(reverse=True)
    return os.path.join(results_dir, dirs[0])


# ================= 页面 Tab 划分 =================
tab1, tab2, tab3 = st.tabs(["📊 质量看板 (RAG诊断)", "🤖 Agent 轨迹回放", "🔍 AI 代码变更审查"])

# ================= Tab 1: 质量看板 =================
with tab1:
    st.subheader("RAG 分层诊断首错归因")

    # 找最新的 rag-layered 结果目录
    rag_dir = get_latest_run_dir("rag-layered")
    if rag_dir:
        st.success(f"已加载真实跑批数据：`{rag_dir}`")
        layer_json_path = os.path.join(rag_dir, "layer_summary.json")

        if os.path.exists(layer_json_path):
            with open(layer_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            dist = data.get("first_failing_distribution", {})
            if dist:
                df_dist = pd.DataFrame(list(dist.items()), columns=["失败层级", "数量"])
                fig = px.bar(df_dist, x="失败层级", y="数量", color="失败层级",
                             title="First Failing Layer 分布",
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("layer_summary.json 中未找到 first_failing_distribution 数据。")
        else:
            st.error(f"在 {rag_dir} 中未找到 layer_summary.json")
    else:
        st.warning("未在 results 目录下找到 RAG 跑批记录，请先运行 `python run.py --task rag-layered ...`")

# ================= Tab 2: Agent 轨迹回放 =================
with tab2:
    st.subheader("Agent 死循环与异常恢复分析")

    agent_dir = get_latest_run_dir("agent-trajectory")
    if agent_dir:
        st.success(f"已加载真实跑批数据：`{agent_dir}`")
        agent_json_path = os.path.join(agent_dir, "agent_report.json")

        if os.path.exists(agent_json_path):
            with open(agent_json_path, "r", encoding="utf-8") as f:
                agent_data = json.load(f)

            # 提取所有 case 的 ID 做成下拉框
            case_ids = [item["id"] for item in agent_data]
            selected_case = st.selectbox("请选择要回放的 Case：", case_ids)

            # 找到选中的那个 case
            case_detail = next((item for item in agent_data if item["id"] == selected_case), None)

            if case_detail:
                st.write(f"**任务状态**: {case_detail['check']['status']}")
                st.write(f"**失败模式**: {case_detail['check'].get('fail_modes', [])}")

                steps = case_detail.get("trajectory", {}).get("steps", [])
                for s in steps:
                    if s.get("type") == "Action":
                        st.code(f"Action: {s.get('tool')}({s.get('args')})", language="python")
                        obs = s.get("observation", "")
                        if "Error" in obs:
                            st.error(f"Observation: {obs}")
                        else:
                            st.success(f"Observation: {obs}")

                if "infinite_loop" in case_detail['check'].get('fail_modes', []):
                    st.warning("🛑 **【门禁判定结果】: FAIL** - 触发 `infinite_loop` 规则，已强制熔断！")
        else:
            st.error(f"在 {agent_dir} 中未找到 agent_report.json")
    else:
        st.warning("未在 results 目录下找到 Agent 跑批记录，请先运行 `python run.py --task agent-trajectory ...`")

# ================= Tab 3: AI 代码变更审查 =================
with tab3:
    st.subheader("AI 代码审查与安全门禁 (AI Code Review)")
    st.markdown(
        "模拟研发提交的 PR 代码。您可以在下方输入框修改或粘贴代码，AI 会自动审查漏洞，**强制引用原代码行作为证据**，并触发拦截。")

    # 默认填入一段带有漏洞的测试代码，方便演示
    default_bad_code = """def get_user_info(username):
    # 漏洞1：硬编码敏感密码
    db_password = "admin123456" 

    # 漏洞2：SQL 注入风险（直接拼接字符串）
    sql = "SELECT * FROM users WHERE username = '" + username + "'"

    cursor.execute(sql)
    return cursor.fetchall()
"""

    # 使用 text_area 让用户可以实时编辑代码
    input_code = st.text_area("📝 待审查代码 (Python):", value=default_bad_code, height=200)

    if st.button("🚀 执行 AI 代码审查", type="primary"):
        if not input_code.strip():
            st.warning("请输入需要审查的代码。")
        elif not executor:
            st.error("大模型未初始化，请检查 .env 中的 API Key")
        else:
            with st.spinner("大模型正在逐行审查代码..."):
                prompt = f"""你是一个资深的代码安全审计专家。
请审查以下代码。如果发现漏洞（如SQL注入、硬编码密码），请必须给出严重等级（高危/低危），并引用原代码的行号作为证据。

【待审查代码】
{input_code}

请严格输出 JSON 格式：
{{"status": "FAIL", "vulnerabilities": [{{"line": "行号", "type": "漏洞类型", "evidence": "原代码片段", "reason": "原因"}}]}}
只输出 JSON，不要其他废话。
"""
                response = executor.call_model(prompt)

                try:
                    # 容错提取 JSON
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