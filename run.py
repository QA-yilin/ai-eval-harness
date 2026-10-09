import argparse
from core.runner import Runner


def main():
    parser = argparse.ArgumentParser(description="AI Eval Harness")
    parser.add_argument("--task", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--config-dir", default="./config")
    parser.add_argument("--results-dir", default="./results")
    args = parser.parse_args()

    runner = Runner(
        config_dir=args.config_dir,
        task_name=args.task,
        model_name=args.model,
        dataset_name=args.dataset,
        results_dir=args.results_dir,
    )
    runner.run()


if __name__ == "__main__":
    main()