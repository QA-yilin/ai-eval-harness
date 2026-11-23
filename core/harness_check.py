"""
Harness 调度体验校验器：路由正确性 / 兜底生效 / 会话隔离 / 适配失败识别。

时效指标复用现有 performance_test(_async).py 的 TTFT、P95 采集结果，
本模块只做调度正确性与容错断言，不重复造压测轮子。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HarnessResult:
    case_id: str
    passed: bool
    labels: List[str] = field(default_factory=list)
    routing_ok: Optional[bool] = None
    fallback_ok: Optional[bool] = None
    isolated: Optional[bool] = None
    latency_p95_ms: Optional[float] = None
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "labels": self.labels,
            "routing_ok": self.routing_ok,
            "fallback_ok": self.fallback_ok,
            "isolated": self.isolated,
            "latency_p95_ms": self.latency_p95_ms,
            "evidence": self.evidence,
        }


class HarnessChecker:
    def check(
        self,
        case: Dict[str, Any],
        routing_tier: Optional[str],
        fallback_model: Optional[str],
        session_isolated: Optional[bool],
        latency_p95_ms: Optional[float],
    ) -> HarnessResult:
        expected = case.get("expected", {})
        res = HarnessResult(case_id=case["id"], passed=True, latency_p95_ms=latency_p95_ms)
        res.evidence = f"route={routing_tier}, fallback={fallback_model}, isolated={session_isolated}"

        # 1. 路由正确性
        expected_tier = expected.get("routing_model_tier")
        if expected_tier is not None:
            res.routing_ok = routing_tier == expected_tier
            if not res.routing_ok:
                res.labels.append("路由错误")

        # 2. 兜底生效
        if expected.get("fallback_expected"):
            res.fallback_ok = fallback_model == expected.get("fallback_model")
            if not res.fallback_ok:
                res.labels.append("兜底未生效")

        # 3. 并发会话隔离
        if "session_isolation" in expected:
            res.isolated = bool(session_isolated)
            if not res.isolated:
                res.labels.append("结果串线")

        # 4. 适配失败识别
        if expected.get("adaptation_failure_detected") is not None:
            detected = bool(expected.get("adaptation_failure_detected"))
            if not detected:
                res.labels.append("场景适配失效")

        # 5. 时效红线
        max_latency = expected.get("max_p95_latency_ms")
        if max_latency is not None and latency_p95_ms is not None and latency_p95_ms > max_latency:
            res.labels.append("响应延迟")

        res.passed = len(res.labels) == 0
        return res
