from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import json
import time
from pathlib import Path

from .agents import AnalystAgent, CriticAgent, PlannerAgent, RetrievalAgent, WriterAgent
from .models import Source, Workspace
from .provider import TextProvider
from .scheduling import estimate_length, task_order


class ResearchOrchestrator:
    def __init__(self, provider: TextProvider | None = None, workers: int = 3, policy: str = "fcfs") -> None:
        if workers < 1:
            raise ValueError("workers must be positive")
        task_order([], policy)
        self.provider = provider
        self.workers = workers
        self.policy = policy

    def run(self, topic: str, sources: list[Source]) -> Workspace:
        workspace = Workspace(topic=topic)
        questions = PlannerAgent(self.provider).run(workspace)
        agents = [RetrievalAgent(index + 1, provider=self.provider) for index in range(len(questions))]
        estimates = [estimate_length(q) for q in questions]
        order = task_order([e.output_units for e in estimates], self.policy)
        ready = time.perf_counter()

        def execute(index):
            wait_ms = (time.perf_counter() - ready) * 1000
            result = agents[index].run(questions[index], sources)
            result[3].details.update(task_id=f"research-{index + 1}", queue_ms=wait_ms,
                                     policy=self.policy, length_bucket=estimates[index].bucket,
                                     estimated_output_units=estimates[index].output_units)
            return index, result

        results = {}
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = [pool.submit(execute, index) for index in order]
            for future in as_completed(futures):
                index, result = future.result()
                results[index] = result
                event = result[3]
                workspace.events.append(event)
        # Restore plan order so concurrency does not change synthesis ordering.
        for index in range(len(questions)):
            question, evidence, note, _ = results[index]
            key = f"research-{index + 1}: {question}"
            workspace.evidence[key] = evidence
            workspace.research_notes[key] = note
        AnalystAgent(self.provider).run(workspace)
        writer = WriterAgent(self.provider)
        writer.run(workspace)
        critic = CriticAgent(self.provider)
        notes = critic.run(workspace)
        if notes and self.provider:
            writer.run(workspace, notes)
            critic.run(workspace)
        return workspace


def save_report(workspace: Workspace, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    trace = ["\n\n## Agent Trace\n", "| Agent | Action | Time (ms) |", "|---|---|---:|"]
    trace.extend(f"| {event.agent} | {event.action} | {event.elapsed_ms:.2f} |" for event in workspace.events)
    audit = "\n\n## Review Status\n\n" + ("Unresolved issues:\n" + "\n".join(f"- {n}" for n in workspace.critique) if workspace.critique else "No issues flagged by the configured critic; this is not a guarantee of factual correctness.")
    path.write_text(workspace.draft + audit + "\n" + "\n".join(trace) + "\n", encoding="utf-8")
    path.with_suffix(".trace.json").write_text(json.dumps([asdict(e) for e in workspace.events], ensure_ascii=False, indent=2), encoding="utf-8")
