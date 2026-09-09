# Prediction-aware scheduling experiment

## Research motivation

Haoyi Niu's [homepage](https://haoyiniu.github.io/) lists work on output-length prediction (Prompt2Length) and GPU job-duration prediction (JDPMHF). This prototype borrows the question of how advance workload estimates might help scheduling. It does not implement either paper's model or reproduce its experiments.

There are two independent components:

1. The research pipeline uses a transparent question-text heuristic to prioritize researcher calls under a worker limit. Its units and thresholds are assumptions, not trained predictions.
2. The simulator varies duration-prediction noise to test scheduling behavior. It does not use the text heuristic. Zero-noise predictions are an oracle reference available only inside simulation.

## Reproduction

Requires Python 3.10+. From the repository root:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m research_agents.benchmark --seeds 20 --tasks 30 --workers 2 --output examples/scheduling_results.csv
```

The committed CSV contains 160 rows: 20 seeds × four noise bounds × two policies. Each seed uses the same actual task durations across all comparisons. Predictions are generated as `actual * (1 + bound * uniform(-1, 1))`, floored at 0.01. A bound of 0.5 means up to ±50% relative noise, not a measured 50% average prediction error. Random draws are shared across noise levels for paired comparisons.

## Assumptions and metrics

- Thirty independent tasks arrive together at time zero and run non-preemptively on two identical worker slots.
- Seventy percent of task draws use uniform durations from 1 to 4; the remainder use 8 to 20. Time units are synthetic.
- FCFS preserves generated order. SJF orders by predicted duration, with input order breaking ties.
- Actual durations advance the simulation clock; the scheduler cannot use them for selection.
- Mean wait is mean start time. Mean completion is mean finish time. Makespan is the latest finish. Slot utilization is total busy time divided by `workers * makespan`; this is not GPU utilization.
- Predictions have no computation overhead here. Network variability, GPU batching, token streaming, dependency constraints and answer quality are not modeled.

## Observed results

Arithmetic means over seeds 0–19, 30 tasks and two workers:

| Relative noise bound | Policy | Mean wait | Mean completion | Makespan | Slot utilization |
|---|---|---:|---:|---:|---:|
| 0 | FCFS | 39.619 | 45.508 | 91.426 | 0.966 |
| 0 | SJF | 20.740 | 26.629 | 92.511 | 0.953 |
| 0.25 | SJF | 21.035 | 26.923 | 92.610 | 0.954 |
| 0.50 | SJF | 21.606 | 27.495 | 92.937 | 0.947 |
| 1.00 | SJF | 24.522 | 30.411 | 91.617 | 0.964 |

FCFS is unaffected by prediction noise and is shown once. For this workload, predicted-shortest-first lowers average waiting time, but does not lower average makespan relative to FCFS. Larger noise bounds degrade its mean waiting time in this sample. These are descriptive simulation results, not a universal performance guarantee or a live-model speedup. Inspect per-seed CSV results before drawing stronger conclusions.

## Next experiment

Use measured API traces to evaluate the question-text heuristic against a constant predictor and a role-average baseline. Separate training and test tasks, measure prediction error, then replay the same test workloads under each scheduling policy. Finally run repeated live comparisons with fixed model, evidence and budget, assessing citation support and answer completeness as well as latency.
