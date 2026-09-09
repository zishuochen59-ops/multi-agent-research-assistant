import re
import time
from collections import Counter

from .models import AgentEvent, Evidence, Source, Workspace
from .provider import TextProvider


TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]+")
STOP = {"about", "after", "also", "and", "are", "can", "does", "for", "from", "how", "into", "its", "the", "their", "this", "what", "when", "with"}


def keywords(text: str) -> set[str]:
    return {word.lower() for word in TOKEN_RE.findall(text) if len(word) > 2 and word.lower() not in STOP}


class Agent:
    name = "agent"

    def record(self, workspace: Workspace, started: float, action: str, **details: object) -> None:
        workspace.events.append(AgentEvent(self.name, action, (time.perf_counter() - started) * 1000, details))


class PlannerAgent(Agent):
    name = "planner"

    def run(self, workspace: Workspace) -> list[str]:
        started = time.perf_counter()
        topic = workspace.topic.rstrip(" ?")
        questions = [
            f"What problem does {topic} address?",
            f"What methods are used in {topic}?",
            f"What benefits and limitations are reported for {topic}?",
        ]
        workspace.questions = questions
        self.record(workspace, started, "decomposed topic", questions=len(questions))
        return questions


class RetrievalAgent(Agent):
    def __init__(self, worker_id: int, limit: int = 3) -> None:
        self.name = f"researcher-{worker_id}"
        self.limit = limit

    def run(self, question: str, sources: list[Source]) -> tuple[str, list[Evidence], AgentEvent]:
        started = time.perf_counter()
        query = keywords(question)
        matches: list[Evidence] = []
        for source in sources:
            sentences = re.split(r"(?<=[.!?])\s+", source.text.strip())
            for sentence in sentences:
                overlap = query & keywords(sentence)
                if overlap:
                    score = len(overlap) / max(1, len(query))
                    matches.append(Evidence(source.source_id, source.title, source.url, sentence.strip(), score))
        matches.sort(key=lambda item: (-item.score, item.source_id, item.excerpt))
        selected = matches[: self.limit]
        event = AgentEvent(self.name, "retrieved evidence", (time.perf_counter() - started) * 1000, {"question": question, "hits": len(selected)})
        return question, selected, event


class AnalystAgent(Agent):
    name = "analyst"

    def run(self, workspace: Workspace) -> str:
        started = time.perf_counter()
        lines = []
        seen: set[tuple[str, str]] = set()
        for question, items in workspace.evidence.items():
            lines.append(f"Question: {question}")
            for item in items:
                key = (item.source_id, item.excerpt)
                if key not in seen:
                    lines.append(f"- {item.excerpt} [{item.source_id}]")
                    seen.add(key)
        workspace.synthesis = "\n".join(lines)
        self.record(workspace, started, "synthesized evidence", unique_items=len(seen))
        return workspace.synthesis


class WriterAgent(Agent):
    name = "writer"

    def __init__(self, provider: TextProvider | None = None) -> None:
        self.provider = provider

    def run(self, workspace: Workspace, revision_notes: list[str] | None = None) -> str:
        started = time.perf_counter()
        if self.provider:
            instruction = "Write a concise Markdown research brief. Every factual claim must end with a source marker such as [S1]. Do not invent facts."
            request = f"Topic: {workspace.topic}\n\nEvidence:\n{workspace.synthesis}"
            if revision_notes:
                request += "\n\nRevise to address:\n- " + "\n- ".join(revision_notes)
            draft = self.provider.complete(instruction, request)
        else:
            items = []
            seen: set[tuple[str, str]] = set()
            for evidence in workspace.evidence.values():
                for item in evidence:
                    key = (item.source_id, item.excerpt)
                    if key not in seen:
                        items.append(item)
                        seen.add(key)
            body = "\n".join(f"- {item.excerpt} [{item.source_id}]" for item in items)
            sources = "\n".join(f"- [{source_id}] {title}: {url}" for source_id, title, url in sorted({(i.source_id, i.title, i.url) for i in items}))
            draft = f"# Research Brief\n\n## Question\n\n{workspace.topic}\n\n## Evidence Summary\n\n{body or '- No matching evidence found.'}\n\n## Sources\n\n{sources or '- None'}"
        workspace.draft = draft
        self.record(workspace, started, "wrote report", revision=bool(revision_notes))
        return draft


class CriticAgent(Agent):
    name = "critic"

    def run(self, workspace: Workspace) -> list[str]:
        started = time.perf_counter()
        known = {item.source_id for values in workspace.evidence.values() for item in values}
        cited = set(re.findall(r"\[(S\d+)\]", workspace.draft))
        notes = []
        unknown = cited - known
        if unknown:
            notes.append("Remove unknown citations: " + ", ".join(sorted(unknown)))
        if known - cited:
            notes.append("Use or remove uncited evidence: " + ", ".join(sorted(known - cited)))
        if not cited:
            notes.append("Add source markers to factual claims.")
        workspace.critique = notes
        self.record(workspace, started, "audited citations", issues=len(notes))
        return notes
