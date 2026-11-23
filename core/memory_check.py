"""
记忆体验校验器：留存 / 冲突取舍 / 一致性 / 冗余 / 边界遗忘。

判定以规则为主（可解释、可复现）；复杂语义判定可在任务层挂现有 LLM-as-Judge。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MemoryResult:
    case_id: str
    passed: bool
    check: str
    labels: List[str] = field(default_factory=list)
    recalled: List[str] = field(default_factory=list)
    violated: List[str] = field(default_factory=list)
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "check": self.check,
            "labels": self.labels,
            "recalled": self.recalled,
            "violated": self.violated,
            "evidence": self.evidence,
        }


class MemoryChecker:
    def check(self, case: Dict[str, Any], final_answer: str) -> MemoryResult:
        expected = case.get("expected", {})
        check_type = expected.get("check", "preference_retention")
        res = MemoryResult(case_id=case["id"], passed=True, check=check_type)
        res.evidence = final_answer[:500]

        must_recall: List[str] = expected.get("must_recall_facts", [])
        forbidden: List[str] = expected.get("forbidden_facts", [])

        res.recalled = [f for f in must_recall if f in final_answer]
        res.violated = [f for f in forbidden if f in final_answer]

        missing = [f for f in must_recall if f not in final_answer]

        if check_type == "conflict_resolution":
            # 冲突取舍：必须采用新事实，不得回退旧事实
            if res.violated:
                res.labels.append("记忆冲突")
            if missing:
                res.labels.append("记忆丢失")
        elif check_type == "consistency":
            if missing:
                res.labels.append("前后不一致")
        elif check_type == "redundancy":
            if missing:
                res.labels.append("记忆丢失")
            if self._is_redundant(final_answer, expected.get("max_repeated_phrases", 1)):
                res.labels.append("冗余记忆")
        elif check_type == "boundary_forget":
            # 边界遗忘：敏感事实不得出现在公开回答中
            if res.violated:
                res.labels.append("记忆错乱")
        else:  # preference_retention
            if missing:
                res.labels.append("记忆丢失")
            if res.violated:
                res.labels.append("记忆偏差")

        res.passed = len(res.labels) == 0
        return res

    @staticmethod
    def _is_redundant(answer: str, max_repeat: int) -> bool:
        # 简易冗余判定：按句号切分，统计重复短句
        sentences = [s.strip() for s in answer.replace("！", "。").split("。") if s.strip()]
        seen: Dict[str, int] = {}
        for s in sentences:
            seen[s] = seen.get(s, 0) + 1
        return any(c > max_repeat for c in seen.values())
