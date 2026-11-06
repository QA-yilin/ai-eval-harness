import os
import time
import requests


class Executor:
    def __init__(self, model_config):
        self.config = model_config
        self.model_type = model_config["type"]

    def call_model(self, prompt, system_prompt=None):
        # 兼容处理：如果 prompt 是 list（多轮 messages），直接透传
        if isinstance(prompt, list):
            messages = prompt
        else:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        if self.model_type == "api":
            return self._call_api(messages)
        elif self.model_type == "ollama":
            combined_prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            return self._call_ollama(combined_prompt)
        raise ValueError(f"未知模型类型: {self.model_type}")

    def _call_api(self, messages):
        api_key = os.environ.get(self.config["api_key_env"])
        if not api_key:
            raise RuntimeError(f"未设置 {self.config['api_key_env']}")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # 清理 messages，防止 422 报错
        clean_messages = []
        for msg in messages:
            if not msg.get("content"):
                continue
            role = msg.get("role", "user")
            if role not in ["system", "user", "assistant"]:
                role = "user"
            clean_messages.append({"role": role, "content": str(msg["content"])})

        payload = {
            "model": self.config["model"],
            "messages": clean_messages,
            "temperature": self.config.get("temperature", 0.0),
            "max_tokens": self.config.get("max_tokens", 1000),
            "stream": False,
        }

        for i in range(3):
            try:
                r = requests.post(self.config["url"], headers=headers, json=payload, timeout=120)

                if r.status_code == 422:
                    print(f"\n❌ [422 报错] 请求参数有问题！")
                    print(f"服务端返回: {r.text}")
                    return None

                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()

            except Exception as e:
                print(f"  重试 {i + 1}/3: {e}")
                time.sleep(2 ** i)
        return None

    def _call_ollama(self, prompt):
        payload = {
            "model": self.config["model"],
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.get("temperature", 0.1),
                "num_predict": self.config.get("max_tokens", 1000),
            },
        }
        for i in range(3):
            try:
                r = requests.post(self.config["url"], json=payload, timeout=120)
                r.raise_for_status()
                return r.json()["response"]
            except Exception as e:
                print(f"  重试 {i + 1}/3: {e}")
                time.sleep(2 ** i)
        return None