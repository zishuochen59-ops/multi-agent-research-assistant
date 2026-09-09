"""Small, transparent scheduling baselines; no trained predictor or GPU control."""

import heapq
import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LengthEstimate:
    bucket: str
    output_units: int


def estimate_length(question: str) -> LengthEstimate:
    """Rule baseline in relative units, NOT measured tokenizer tokens.

    Cue weights and bucket boundaries are assumptions to test, not paper results.
    """
    units = 80 + 4 * len(re.findall(r"\w+", question))
    lower = question.lower()
    if any(cue in lower for cue in ("compare", "limitations", "detailed", "比较", "局限", "详细")):
        units += 160
    if any(cue in lower for cue in ("methods", "explain", "方法", "解释")):
        units += 80
    return LengthEstimate("short" if units < 160 else "medium" if units < 280 else "long", units)


def task_order(estimates: list[float], policy: str) -> list[int]:
    if policy not in ("fcfs", "sjf"):
        raise ValueError("policy must be fcfs or sjf")
    if any(not math.isfinite(x) or x <= 0 for x in estimates):
        raise ValueError("estimates must be finite and positive")
    indices = list(range(len(estimates)))
    return indices if policy == "fcfs" else sorted(indices, key=lambda i: (estimates[i], i))


@dataclass(frozen=True)
class ScheduledTask:
    task_id: int
    worker: int
    start: float
    finish: float


def simulate(actual: list[float], predicted: list[float], workers: int, policy: str) -> dict:
    """Non-preemptive batch scheduling on identical slots; all tasks arrive at 0.

    Units are simulated time units. Actual durations only advance the clock;
    SJF selects tasks solely from predicted durations.
    """
    if workers < 1 or len(actual) != len(predicted) or not actual:
        raise ValueError("need positive workers and nonempty aligned durations")
    if any(not math.isfinite(x) or x <= 0 for x in actual):
        raise ValueError("actual durations must be finite and positive")
    slots = [(0.0, i) for i in range(workers)]
    heapq.heapify(slots)
    events = []
    for task_id in task_order(predicted, policy):
        start, worker = heapq.heappop(slots)
        finish = start + actual[task_id]
        events.append(ScheduledTask(task_id, worker, start, finish))
        heapq.heappush(slots, (finish, worker))
    makespan = max(e.finish for e in events)
    return {
        "mean_wait": sum(e.start for e in events) / len(events),
        "mean_completion": sum(e.finish for e in events) / len(events),
        "makespan": makespan,
        "slot_utilization": sum(actual) / (workers * makespan),
        "prediction_mae": sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual),
        "events": events,
    }
