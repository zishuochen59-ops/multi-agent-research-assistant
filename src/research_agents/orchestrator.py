from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .agents import AnalystAgent, CriticAgent, PlannerAgent, RetrievalAgent, WriterAgent
from .models import Source, Workspace
from .provider import TextProvider


class ResearchOrchestrator:
    def __init__(self, provider: TextProvider | None = None, workers: int = 3) -> None:
        self.provider = provider
        self.workers = workers

    def run(self, topic: str, sources: list[Source]) -> Workspace:
        workspace = Workspace(topic=topic)
        questions = PlannerAgent(self.provider).run(workspace)
        agents = [RetrievalAgent(index + 1, provider=self.provider) for index in range(len(questions))]
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = [pool.submit(agent.run, question, sources) for agent, question in zip(agents, questions)]
            for future in futures:
                question, evidence, note, event = future.result()
                workspace.evidence[question] = evidence
                workspace.research_notes[question] = note
                workspace.events.append(event)
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
    path.write_text(workspace.draft + "\n" + "\n".join(trace) + "\n", encoding="utf-8")
