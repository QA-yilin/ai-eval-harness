import json
import os
from datetime import datetime


class Reporter:
    def __init__(self, results_dir, task_name, model_name, dataset_name):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"{ts}_{task_name}_{model_name}_{dataset_name}"
        self.run_dir = os.path.join(results_dir, self.run_id)
        os.makedirs(self.run_dir, exist_ok=True)

    def save_config(self, config):
        with open(os.path.join(self.run_dir, "config_snapshot.json"), "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def save_results(self, name, data):
        path = os.path.join(self.run_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_markdown(self, name, content):
        path = os.path.join(self.run_dir, f"{name}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def get_run_dir(self):
        return self.run_dir