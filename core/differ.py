import json
import os


class Differ:
    """对比两次运行的指标变化"""

    def __init__(self, run_a_dir, run_b_dir):
        self.run_a_dir = run_a_dir
        self.run_b_dir = run_b_dir

    def compare(self):
        a = self._load_run(self.run_a_dir)
        b = self._load_run(self.run_b_dir)
        return {
            "run_a": os.path.basename(self.run_a_dir),
            "run_b": os.path.basename(self.run_b_dir),
            "metrics_diff": self._diff_metrics(a, b),
            "per_case_diff": self._diff_per_case(a, b),
        }

    def _load_run(self, run_dir):
        """加载一次运行的所有结果"""
        data = {"dir": run_dir}
        for name in ["layer_summary", "retrieval_report", "understanding_report",
                     "generation_report", "kappa_report", "agent_report",
                     "injection_summary", "config_snapshot"]:
            path = os.path.join(run_dir, f"{name}.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data[name] = json.load(f)
        return data

    def _diff_metrics(self, a, b):
        """对比关键指标"""
        diffs = []

        # RAG 分层：first_failing_layer 分布
        a_summary = a.get("layer_summary", {}).get("first_failing_distribution", {})
        b_summary = b.get("layer_summary", {}).get("first_failing_distribution", {})
        if a_summary or b_summary:
            all_layers = set(a_summary) | set(b_summary)
            for layer in all_layers:
                av = a_summary.get(layer, 0)
                bv = b_summary.get(layer, 0)
                diffs.append({
                    "metric": f"first_failing.{layer}",
                    "a": av, "b": bv, "delta": bv - av,
                    "direction": self._direction(bv - av, lower_better=True),
                })

        # Judge 校准：Kappa / MAE
        a_kappa = a.get("kappa_report", {})
        b_kappa = b.get("kappa_report", {})
        if a_kappa or b_kappa:
            for key, lower_better in [("cohen_kappa", False), ("mae", True), ("raw_agreement", False)]:
                av = a_kappa.get(key)
                bv = b_kappa.get(key)
                if av is not None and bv is not None:
                    diffs.append({
                        "metric": f"judge.{key}",
                        "a": av, "b": bv, "delta": round(bv - av, 3),
                        "direction": self._direction(bv - av, lower_better),
                    })

        # Prompt 注入：防御成功率
        a_inj = a.get("injection_summary", {})
        b_inj = b.get("injection_summary", {})
        if a_inj or b_inj:
            av = a_inj.get("rate")
            bv = b_inj.get("rate")
            if av is not None and bv is not None:
                diffs.append({
                    "metric": "injection.defense_rate",
                    "a": av, "b": bv, "delta": round(bv - av, 3),
                    "direction": self._direction(bv - av, lower_better=False),
                })

        return diffs

    def _diff_per_case(self, a, b):
        """对比逐条用例的状态变化"""
        changes = []

        # Agent 轨迹
        a_agent = {r["id"]: r["check"]["status"] for r in a.get("agent_report", [])}
        b_agent = {r["id"]: r["check"]["status"] for r in b.get("agent_report", [])}
        for cid in set(a_agent) & set(b_agent):
            if a_agent[cid] != b_agent[cid]:
                changes.append({
                    "case_id": cid, "type": "agent_trajectory",
                    "a": a_agent[cid], "b": b_agent[cid],
                })

        # RAG 分层
        a_rag = {r["id"]: r["first_failing_layer"] for r in a.get("layer_summary", {}).get("per_case", [])}
        b_rag = {r["id"]: r["first_failing_layer"] for r in b.get("layer_summary", {}).get("per_case", [])}
        for cid in set(a_rag) & set(b_rag):
            if a_rag[cid] != b_rag[cid]:
                changes.append({
                    "case_id": cid, "type": "rag_layered",
                    "a": a_rag[cid], "b": b_rag[cid],
                })

        return changes

    def _direction(self, delta, lower_better):
        if delta == 0:
            return "unchanged"
        if lower_better:
            return "improved" if delta < 0 else "regressed"
        return "improved" if delta > 0 else "regressed"