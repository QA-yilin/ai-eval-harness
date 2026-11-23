"""
Agent 轨迹解析器（在现有 core/tools.py 执行引擎基础上扩展）。

输入：执行引擎产出的原始轨迹（Thought/Action/Observation 序列）
输出：结构化 trace，供 agent_attribution.py 做归因断言。

适配说明：若现有 executor.run() 返回的轨迹字段名不同，只需要在
normalize_trace() 里做一层字段映射，归因逻辑无需改动。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TraceStep:
    round: int
    thought: str = ""
    tool: Optional[str] = None
    tool_args: Dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    is_interrupted: bool = False


@dataclass
class AgentTrace:
    case_id: str
    steps: List[TraceStep] = field(default_factory=list)
    final_answer: str = ""
    interrupted: bool = False

    def called_tools(self) -> List[str]:
        return [s.tool for s in self.steps if s.tool]

    def trajectory_text(self) -> str:
        return "\n".join(
            f"[R{s.round}] Thought: {s.thought} | Action: {s.tool} | Obs: {s.observation}"
            for s in self.steps
        )


_ACTION_PATTERN = re.compile(r"Action\s*:\s*([\w\.]+)\s*(?:\((.*?)\))?", re.S)


def _parse_tool_args(raw: str) -> Dict[str, Any]:
    """轻量解析工具入参；复杂结构可替换为 json/ast 解析。"""
    args: Dict[str, Any] = {}
    if not raw:
        return args
    for kv in re.findall(r"(\w+)\s*=\s*['\"]?(.*?)['\"]?\s*(?:,|$)", raw):
        args[kv[0]] = kv[1]
    return args


def normalize_step(index: int, raw: Dict[str, Any]) -> TraceStep:
    return TraceStep(
        round=index,
        thought=raw.get("thought", "") or raw.get("Thought", ""),
        tool=raw.get("tool") or raw.get("Action"),
        tool_args=raw.get("tool_args") or _parse_tool_args(raw.get("args", "")),
        observation=raw.get("observation", "") or raw.get("Observation", ""),
        is_interrupted=bool(raw.get("interrupted", False)),
    )


def build_trace(case_id: str, raw_trace: List[Dict[str, Any]], final_answer: str = "") -> AgentTrace:
    trace = AgentTrace(case_id=case_id, final_answer=final_answer)
    for i, raw in enumerate(raw_trace or [], start=1):
        step = normalize_step(i, raw)
        trace.steps.append(step)
        trace.interrupted = trace.interrupted or step.is_interrupted
    return trace
