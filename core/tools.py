# core/tools.py
import time

class ToolRegistry:
    @staticmethod
    def get_weather(city: str) -> str:
        time.sleep(0.1)
        if "北京" in city:
            return "北京今天小雨，气温 15 度，建议带伞。"
        elif "上海" in city:
            return "上海今天晴，气温 25 度，不需要带伞。"
        else:
            raise ValueError(f"未找到城市 '{city}' 的天气数据，请检查城市名是否正确。")

    @staticmethod
    def calculate_exchange(amount: float, currency: str) -> str:
        if currency == "USD":
            return f"{amount} 美元 = {amount * 7.2:.2f} 人民币"
        else:
            raise ValueError(f"不支持 {currency} 的汇率计算")

    @classmethod
    def execute(cls, tool_name: str, tool_args: dict) -> str:
        try:
            func = getattr(cls, tool_name, None)
            if not func:
                return f"Error: 工具 '{tool_name}' 不存在"
            result = func(**tool_args)
            return str(result)
        except Exception as e:
            # 所有错误转为 Observation 返回给模型，测试模型容错
            return f"Error: {str(e)}"