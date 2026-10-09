import os
import yaml
from core.executor import Executor
from core.evaluator import Evaluator
from core.reporter import Reporter


class Runner:
    def __init__(self, config_dir, task_name, model_name, dataset_name, results_dir):
        self.config_dir = config_dir
        self.task_name = task_name
        self.model_name = model_name
        self.dataset_name = dataset_name
        self.results_dir = results_dir

        self.models = self._load_yaml("models.yaml")["models"]
        self.datasets = self._load_yaml("datasets.yaml")["datasets"]
        self.tasks = self._load_yaml("tasks.yaml")["tasks"]

    def _load_yaml(self, name):
        with open(os.path.join(self.config_dir, name), "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def run(self):
        task_cfg = self.tasks[self.task_name]
        model_cfg = self.models[self.model_name]
        dataset_cfg = self.datasets[self.dataset_name]

        executor = Executor(model_cfg)
        evaluator = Evaluator()
        reporter = Reporter(self.results_dir, self.task_name, self.model_name, self.dataset_name)

        reporter.save_config({
            "task": self.task_name,
            "model": self.model_name,
            "dataset": self.dataset_name,
            "task_config": task_cfg,
            "model_config": {k: v for k, v in model_cfg.items() if k != "api_key_env"},
            "dataset_config": dataset_cfg,
        })

        if self.task_name == "rag-layered":
            from tasks.rag_task import run_rag_task
            run_rag_task(task_cfg, executor, evaluator, reporter, dataset_cfg)
        elif self.task_name == "judge-calibration":
            from tasks.judge_task import run_judge_task
            run_judge_task(task_cfg, executor, evaluator, reporter, dataset_cfg)
        elif self.task_name == "agent-trajectory":
            from tasks.agent_task import run_agent_task
            run_agent_task(task_cfg, executor, evaluator, reporter, dataset_cfg)
        elif self.task_name == "prompt-injection":
            from tasks.injection_task import run_injection_task
            run_injection_task(task_cfg, executor, evaluator, reporter, dataset_cfg)

        else:
            raise ValueError(f"未知任务: {self.task_name}")

        print(f"\n运行完成，结果目录：{reporter.get_run_dir()}")

