import streamlit as st
import json
import os
import yaml
import plotly.express as px
import pandas as pd
from core.executor import Executor
from dotenv import load_dotenv
from core.image_guard import AIGCImageGuard

load_dotenv()

# ================= 页面基础配置 =================
st.set_page_config(page_title="AI 工程效能与质量门禁平台", page_icon="🛡️", layout="wide")

# ================= 新增：自定义 CSS 去除顶部留白 =================
st.markdown("""
    <style>
        /* 减少顶部主容器的 padding */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 0rem !important;
        }
        /* 隐藏 Streamlit 默认的顶部工具栏（可选） */
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)
# =================================================================

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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 质量看板 (RAG诊断)", "🤖 Agent 轨迹回放", "🔍 AI 代码变更审查", "🖼️ AIGC图像质检", "⚡LLM接口性能压测看板"])

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

# ================= Tab 4: AIGC 图像防伪 =================
with tab4:
    st.subheader("🖼️ AIGC 图像防伪质检 (PHash)")
    st.markdown("针对 AIGC 电商场景，使用感知哈希 (PHash) 提取图像结构特征，精准识别像素级篡改。")

    col1, col2 = st.columns(2)
    with col1:
        # 注意看，大屏展示图片也用到了根目录拼接
        st.image(os.path.join("datasets", "images", "official_bag.png"), caption="官方原图", width=300)
    with col2:
        st.image(os.path.join("datasets", "images", "tampered_bag.png"), caption="被篡改图 (标签被改)", width=300)

    if st.button("🚀 执行图像防伪校验"):
        guard = AIGCImageGuard()
        res = guard.verify_image_integrity("datasets/images/official_bag.png", "datasets/images/tampered_bag.png")

        if res["status"] == "FAIL":
            st.error(res["message"])
            st.write(f"**差异值**: `{res['diff_score']}` (阈值: 5)")
        else:
            st.success(res["message"])

# ================= Tab5 ⚡ LLM接口性能压测【新增】 =================
with tab5:
    st.subheader("⚡ LLM流式接口性能压测（TTFT / 总耗时）")
    perf_dir = get_latest_run_dir("perf_deepseek_async")
    if perf_dir:
        st.success(f"加载最新压测结果目录：`{perf_dir}`")
        report_path = os.path.join(perf_dir, "perf_test_report.json")
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                perf_report = json.load(f)

            # 基础汇总，改用markdown表格，完全普通文本，字号和其他tab一模一样
            st.markdown("#### 📋 基础汇总")
            md_table = f"""
|总请求数|最大并发|成功数|失败数|成功率(%)|
|---|---|---|---|---|
|{perf_report["total"]}|{perf_report["max_concurrency"]}|{perf_report["success_count"]}|{perf_report["error_count"]}|{perf_report["success_rate"]}|
"""
            st.markdown(md_table)

            st.divider()
            ttft_stats = perf_report.get("ttft_stats", {})
            total_stats = perf_report.get("total_time_stats", {})

            if ttft_stats and total_stats:
                st.markdown("### 🕐 TTFT首字延迟统计 (ms)")
                ttft_md = f"""
|平均TTFT|P50|P90|P95|P99|最小值|最大值|
|---|---|---|---|---|---|---|
|{ttft_stats["mean"]}|{ttft_stats["p50"]}|{ttft_stats["p90"]}|{ttft_stats["p95"]}|{ttft_stats["p99"]}|{ttft_stats["min"]}|{ttft_stats["max"]}|
"""
                st.markdown(ttft_md)

                st.markdown("### ⏱️ 请求完整总耗时统计 (ms)")
                total_md = f"""
|平均总耗时|P50|P95|最小值|最大值|
|---|---|---|---|---|
|{total_stats["mean"]}|{total_stats["p50"]}|{total_stats["p95"]}|{total_stats["min"]}|{total_stats["max"]}|
"""
                st.markdown(total_md)

                # 原始明细dataframe绘图
                details_df = pd.DataFrame(perf_report["details"])
                success_df = details_df[details_df["status"]=="success"]

                st.divider()
                st.markdown("#### 📈 TTFT分布直方图（成功请求）")
                fig_ttft = px.histogram(success_df, x="ttft", nbins=20, title="TTFT(ms)分布", color_discrete_sequence=["#4C78A8"])
                st.plotly_chart(fig_ttft, use_container_width=True)

                st.markdown("#### 📈 完整总耗时分布直方图（成功请求）")
                fig_total = px.histogram(success_df, x="total_time", nbins=20, title="总耗时(ms)分布", color_discrete_sequence=["#72B7B2"])
                st.plotly_chart(fig_total, use_container_width=True)

                with st.expander("🔍 查看全部原始请求明细"):
                    st.dataframe(details_df, use_container_width=True)

                error_df = details_df[details_df["status"]!="success"]
                if len(error_df)>0:
                    with st.expander(f"⚠️ 错误样本（共{len(error_df)}条）"):
                        st.dataframe(error_df, use_container_width=True)
            else:
                st.info("报告内无成功统计数据，全部请求失败（如余额不足402），可展开查看details明细")
                with st.expander("🔍 全部原始请求明细"):
                    st.dataframe(pd.DataFrame(perf_report["details"]), use_container_width=True)
        else:
            st.error(f"目录下找不到 perf_test_report.json : {perf_dir}")
    else:
        st.warning("尚未找到性能压测结果，请在终端执行：`python performance_test_async.py` 生成results下压测报告")