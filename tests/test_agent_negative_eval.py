"""
单元测试：agent‑negative evaluator边界逻辑
业务约束初衷：
1. clarification_required=True 仅豁免 planning_error；wrong_tool_call / infinite_loop 依旧生效
2. 工具报错后紧跟相同工具重试：sanitized_tools过滤，不产生planning_error；但超过次数依然命中infinite_loop
3. expected_steps=[] 空期望，不触发planning_error
"""
import json
from core.evaluator import Evaluator


def test_agent_negative_evaluator_boundary():
    evaluator = Evaluator()

    test_cases = [
        # BN01：工具Error后合法重试1次，不应打planning_error，PASS
        {
            "id": "BN01",
            "expected_steps": ["get_weather", "reply"], # 修正：移除多余一次get_weather
            "tools": ["get_weather"],
            "clarification_required": False,
            "trajectory": {
                "steps": [
                    {"type":"Action","tool":"get_weather","args":{"city":"Beijing"},"observation":"Error: service down"},
                    {"type":"Action","tool":"get_weather","args":{"city":"Beijing"},"observation":"ok"},
                    {"type":"Action","tool":"reply","args":{"content":"ok"},"observation":"END"},
                ]
            }
        },

        # BN02：同一工具连续多次重试，命中 infinite_loop，FAIL
        {
            "id": "BN02",
            "expected_steps": ["get_weather", "reply"],
            "tools": ["get_weather"],
            "clarification_required": False,
            "trajectory": {
                "steps": [
                    {"type":"Action","tool":"get_weather","args":{"city":"Beijing"},"observation":"Error"},
                    {"type":"Action","tool":"get_weather","args":{"city":"Beijing"},"observation":"Error"},
                    {"type":"Action","tool":"get_weather","args":{"city":"Beijing"},"observation":"Error"},
                    {"type":"Action","tool":"get_weather","args":{"city":"Beijing"},"observation":"Error"},
                    {"type":"Action","tool":"reply","args":{"content":"fail"},"observation":"END"},
                ]
            }
        },
        # BN03A：clarification_required=true，仅reply澄清，PASS，无planning_error
        {
            "id": "BN03A",
            "expected_steps": ["calculate_exchange", "get_weather", "reply"],
            "tools": ["calculate_exchange", "get_weather"],
            "clarification_required": True,
            "trajectory": {
                "steps": [
                    {"type":"Action","tool":"reply","args":{"content":"请补充城市"},"observation":"END"},
                ]
            }
        },
        # BN03B：clarification_required=true，但调用非法工具；应当打出 wrong_tool_call，FAIL
        {
            "id": "BN03B",
            "expected_steps": ["calculate_exchange", "get_weather", "reply"],
            "tools": ["calculate_exchange", "get_weather"],
            "clarification_required": True,
            "trajectory": {
                "steps": [
                    {"type":"Action","tool":"hack_tool","args":{},"observation":"xxx"},
                    {"type":"Action","tool":"reply","args":{"content":"请补充城市"},"observation":"END"},
                ]
            }
        },
        # BN04：expected_steps为空数组，不需要调用工具，PASS
        {
            "id": "BN04",
            "expected_steps": [],
            "tools": ["get_weather"],
            "clarification_required": True,
            "trajectory": {
                "steps": [
                    {"type":"Action","tool":"reply","args":{"content":"请告诉我城市"},"observation":"END"},
                ]
            }
        }
    ]

    eval_result = evaluator.evaluate("agent_negative", test_cases)
    per_case = {item["id"]: item for item in eval_result["per_case"]}

    # --------断言校验--------
    # BN01 PASS，无 planning_error
    bn01 = per_case["BN01"]
    assert bn01["status"] == "PASS", f"BN01 预期PASS，实际 {bn01['status']}"
    assert "planning_error" not in bn01["fail_modes"]

    # BN02 FAIL，包含 infinite_loop
    bn02 = per_case["BN02"]
    assert bn02["status"] == "FAIL"
    assert "infinite_loop" in bn02["fail_modes"]

    # BN03A PASS
    bn03a = per_case["BN03A"]
    assert bn03a["status"] == "PASS"
    assert len(bn03a["fail_modes"]) == 0

    # BN03B FAIL，包含 wrong_tool_call；澄清标记不屏蔽非法工具
    bn03b = per_case["BN03B"]
    assert bn03b["status"] == "FAIL"
    assert "wrong_tool_call" in bn03b["fail_modes"]

    # BN04 PASS，空expected_steps
    bn04 = per_case["BN04"]
    assert bn04["status"] == "PASS"

    print("✅ all agent‑negative boundary test passed")


if __name__ == "__main__":
    test_agent_negative_evaluator_boundary()
