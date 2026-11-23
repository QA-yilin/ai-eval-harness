"""
Agent 失败归因断言器。

对照用例期望动作序列，自动判定：
  漏执行 / 工具错选 / 参数错误 / 死循环 / 过早终止 / 答非所问 / 逻辑混乱
复用现有 README 中已落地的 5 类归因，并扩展交互与逻辑类标签。

用法（在 tasks/agent_task.py 中调用）：
    result = AttributionJudge().judge(case, trace, final_answer)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.agent_trace import AgentTrace


@dataclass
class AttributionResult:
    case_id: str
    passed: bool
    matched_tools: List[str] = field(default_factory=list)
    missing_tools: List[str] = field(default_factory=list)
    forbidden_called: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "matched_tools": self.matched_tools,
            "missing_tools": self.missing_tools,
            "forbidden_called": self.forbidden_called,
            "labels": self.labels,
            "evidence": self.evidence,
        }


class AttributionJudge:
    DEAD_LOOP_MAX_REPEAT = 3  # 同一工具+相近入参连续重复次数阈值

    def judge(self, case: Dict[str, Any], trace: AgentTrace, final_answer: str) -> AttributionResult:
        expected = case.get("expected", {})
        res = AttributionResult(case_id=case["id"], passed=True)

        expected_tools: List[str] = expected.get("expected_tools", [])
        forbidden_tools: List[str] = expected.get("forbidden_tools", [])
        actual_tools = trace.called_tools()

        res.missing_tools = [t for t in expected_tools if t not in actual_tools]
        res.forbidden_called = [t for t in forbidden_tools if t in actual_tools]
        res.matched_tools = [t for t in expected_tools if t in actual_tools]

        # 1. 漏执行：期望工具未调用
        if res.missing_tools:
            res.labels.append("漏执行")

        # 2. 错调用：调用了禁用工具
        if res.forbidden_called:
            res.labels.append("错调用")

        # 3. 死循环：同工具重复触发超阈值
        if self._is_dead_loop(trace):
            res.labels.append("死循环")

        # 4. 过早终止：轨迹被中断且期望动作未完成
        if trace.interrupted and res.missing_tools:
            res.labels.append("过早终止")

        # 5. 必须澄清但直接执行
        if expected.get("must_clarify") and not self._asked_clarification(trace, final_answer):
            res.labels.append("逻辑混乱")

        # 6. 答非所问：期望关键词未出现在最终回答/轨迹中
        keywords = expected.get("expected_trajectory_keywords", [])
        if keywords and not any(k in (final_answer + trace.trajectory_text()) for k in keywords):
            res.labels.append("答非所问")

        # 7. 参数错误：调用了期望工具但关键入参缺失（由任务层在 tool_args 里标记 missing）
        if self._has_missing_args(trace):
            res.labels.append("参数错误")

        res.passed = len(res.labels) == 0
        res.evidence = trace.trajectory_text()[:500]
        return res

    def _is_dead_loop(self, trace: AgentTrace) -> bool:
        seen: Dict[str, int] = {}
        for step in trace.steps:
            if not step.tool:
                continue
            key = f"{step.tool}:{sorted(step.tool_args.items())}"
            seen[key] = seen.get(key, 0) + 1
            if seen[key] >= self.DEAD_LOOP_MAX_REPEAT:
                return True
        return False

    @staticmethod
    def _asked_clarification(trace: AgentTrace, final_answer: str) -> bool:
        text = final_answer + trace.trajectory_text()
        return any(w in text for w in ["确认", "澄清", "请问", "哪一份", "哪位"])

    @staticmethod
    def _has_missing_args(trace: AgentTrace) -> bool:
        return any(step.tool_args.get("missing") for step in trace.steps)
