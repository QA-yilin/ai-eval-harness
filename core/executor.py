import os
import time
import requests


class Executor:
    def __init__(self, model_config):
        self.config = model_config
        self.model_type = model_config["type"]

    def call_model(self, prompt, system_prompt=None):
        if self.model_type == "api":
            return self._call_api(prompt, system_prompt)
        elif self.model_type == "ollama":
            return self._call_ollama(prompt, system_prompt)
        raise ValueError(f"未知模型类型: {self.model_type}")

    def _call_api(self, prompt, system_prompt=None):
        api_key = os.environ.get(self.config["api_key_env"])
        if not api_key:
            raise RuntimeError(f"未设置 {self.config['api_key_env']}")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config["model"],
            "messages": messages,
            "temperature": self.config.get("temperature", 0.0),
            "max_tokens": self.config.get("max_tokens", 1000),
            "stream": False,
        }
        for i in range(3):
            try:
                r = requests.post(self.config["url"], headers=headers,
                                  json=payload, timeout=120)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"  重试 {i+1}/3: {e}")
                time.sleep(2 ** i)
        return None

    def _call_ollama(self, prompt, system_prompt=None):
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
                print(f"  重试 {i+1}/3: {e}")
                time.sleep(2 ** i)
        return None