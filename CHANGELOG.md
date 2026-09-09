# Project evolution log

[![English](https://img.shields.io/badge/Language-English-2563EB)](CHANGELOG.md)
[![Chinese](https://img.shields.io/badge/Language-Chinese-DC2626)](CHANGELOG.zh-CN.md)

This log records the project's functional evolution from the repository's actual commit history. All entries below were completed on 9 September 2026.

## Trainable output-length baseline

Commit [`6bc7dea`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/6bc7dea)

- Added a dependency-free standardized-ridge baseline that predicts relative output length from prompt features.
- Added configurable normal-distribution-based label filtering and semantic length-cue substitutions.
- Added a deterministic 28-record bilingual synthetic dataset and held-out evaluation command.
- Connected saved models to SJF researcher scheduling through `--length-model`.
- Added estimator provenance to researcher traces and expanded automated coverage from twelve to fifteen tests.

This is an inspectable undergraduate baseline inspired by the public Prompt2Length description. It does not implement the paper's DistilBERT architecture or reproduce its reported benchmarks.

## Documentation separation

Commit [`4369baa`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/4369baa)

- Split the mixed README into independent English and Chinese editions.
- Added language-selection buttons to both editions.
- Added localized English and Chinese output to the scheduling demonstration.

## Executable scheduling demonstration

Commit [`2ea222b`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/2ea222b)

- Added a runnable one-worker, three-task FCFS versus SJF example.
- Documented execution order, mean waiting time and makespan.
- Explained why limited concurrency is required for ordering to matter.

## Prediction-aware scheduling experiment

Commits [`386b0bb`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/386b0bb), [`201a70e`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/201a70e) and [`0867caf`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/0867caf)

- Added FCFS and predicted-shortest-first researcher scheduling with configurable worker limits.
- Added a transparent question-length heuristic that returns relative units and length buckets.
- Added structured task traces containing queue time, policy, task ID and predicted length information.
- Added provider-side logging for returned token counts and end-to-end call latency.
- Added a reproducible synthetic experiment covering 20 seeds and four prediction-noise bounds.
- Documented the simulator's assumptions, metrics, results and limitations.
- Expanded automated coverage from four tests to twelve.
- Added basic Chinese lexical retrieval using character bigrams and Chinese sentence punctuation.

The experiment is a synthetic scheduling study. It does not reproduce Prompt2Length or JDPMHF, train a duration predictor, control a GPU cluster or establish a live inference speedup.

## Model coordination across agent roles

Commit [`5250e24`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/5250e24)

- Extended live model calls to the planner, researchers, analyst, writer and critic.
- Added research notes to the shared workspace.
- Added one writer revision after critic feedback.

## Explainable multi-agent pipeline

Commits [`03d285d`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/03d285d) and [`370710d`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/370710d)

- Implemented planner, retrieval, analysis, writing and citation-review roles.
- Added typed source, evidence, event and workspace models.
- Ran retrieval roles concurrently through a thread pool.
- Added deterministic offline sources, Markdown report output, an execution trace and initial tests.
- Added installation, offline demonstration and live-provider documentation.

## Repository start

Commit [`14d2059`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/14d2059)

- Established the project scope as an undergraduate exploration of explainable multi-agent research workflows.
