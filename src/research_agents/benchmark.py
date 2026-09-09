"""Reproducible synthetic sensitivity experiment: python -m research_agents.benchmark."""

import argparse
import csv
import random
from pathlib import Path

from .scheduling import simulate


def experiment(seeds: int = 20, tasks: int = 30, workers: int = 2) -> list[dict]:
    if min(seeds, tasks, workers) < 1:
        raise ValueError("seeds, tasks and workers must be positive")
    rows = []
    for seed in range(seeds):
        rng = random.Random(seed)
        actual = [rng.uniform(1, 4) if rng.random() < 0.7 else rng.uniform(8, 20) for _ in range(tasks)]
        # Same workload and same noise draws for each policy and noise level.
        noise = [rng.uniform(-1, 1) for _ in actual]
        for error in (0.0, 0.25, 0.5, 1.0):
            predicted = [max(0.01, a * (1 + error * n)) for a, n in zip(actual, noise)]
            for policy in ("fcfs", "sjf"):
                metrics = simulate(actual, predicted, workers, policy)
                metrics.pop("events")
                rows.append(dict(seed=seed, tasks=tasks, workers=workers, noise_bound=error, policy=policy, **metrics))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--tasks", type=int, default=30)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--output", type=Path, default=Path("reports/scheduling.csv"))
    args = parser.parse_args()
    try:
        rows = experiment(args.seeds, args.tasks, args.workers)
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} synthetic simulation rows to {args.output}")


if __name__ == "__main__":
    main()
