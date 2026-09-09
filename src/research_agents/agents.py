from __future__ import annotations

import re
import time

from .models import AgentEvent, Evidence, Source, Workspace
from .provider import TextProvider


TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]+")
STOP = {"about", "after", "also", "and", "are", "can", "does", "for", "from", "how", "into", "its", "the", "their", "this", "what", "when", "with"}


def keywords(text: str) -> set[str]:
    terms = {word.lower() for word in TOKEN_RE.findall(text) if len(word) > 2 and word.lower() not in STOP}
    for segment in re.findall(r"[\u4e00-\u9fff]+", text):
        terms.update(segment[i:i + 2] for i in range(len(segment) - 1))
    return terms


class Agent:
    name = "agent"

    def record(self, workspace: Workspace, started: float, action: str, **details: object) -> None:
        workspace.events.append(AgentEvent(self.name, action, (time.perf_counter() - started) * 1000, details))


class PlannerAgent(Agent):
    name = "planner"

    def __init__(self, provider: TextProvider | None = None) -> None:
        self.provider = provider

    def run(self, workspace: Workspace) -> list[str]:
        started = time.perf_counter()
        topic = workspace.topic.rstrip(" ?")
        questions = []
        if self.provider:
            response = self.provider.complete(
                "You are a research planner. Return exactly three focused research questions, one per line, without numbering.",
                topic,
            )
            questions = [re.sub(r"^[-*\d.)\s]+", "", line).strip() for line in response.splitlines() if line.strip()][:3]
        if len(questions) != 3:
            questions = [
                f"What problem does {topic} address?",
                f"What methods are used in {topic}?",
                f"What benefits and limitations are reported for {topic}?",
            ]
        workspace.questions = questions
        self.record(workspace, started, "decomposed topic", questions=len(questions))
        return questions


class RetrievalAgent(Agent):
    def __init__(self, worker_id: int, limit: int = 3, provider: TextProvider | None = None) -> None:
        self.name = f"researcher-{worker_id}"
        self.limit = limit
        self.provider = provider

    def run(self, question: str, sources: list[Source]) -> tuple[str, list[Evidence], str, AgentEvent]:
        started = time.perf_counter()
        query = keywords(question)
        matches: list[Evidence] = []
        for source in sources:
            sentences = re.split(r"(?<=[.!?])\s+|(?<=[。！？])", source.text.strip())
            for sentence in sentences:
                overlap = query & keywords(sentence)
                if overlap:
                    score = len(overlap) / max(1, len(query))
                    matches.append(Evidence(source.source_id, source.title, source.url, sentence.strip(), score))
        matches.sort(key=lambda item: (-item.score, item.source_id, item.excerpt))
        selected = matches[: self.limit]
        packet = "\n".join(f"[{item.source_id}] {item.excerpt}" for item in selected)
        if self.provider:
            note = self.provider.complete(
                "You are an evidence researcher. Answer only from the supplied excerpts. Cite every claim with its source ID. If there is no evidence, say so and do not answer from memory.",
                f"Question: {question}\n\nExcerpts:\n{packet or 'No matching excerpts.'}",
            )
        else:
            note = packet or "No matching evidence found."
        event = AgentEvent(self.name, "retrieved evidence", (time.perf_counter() - started) * 1000, {"question": question, "hits": len(selected)})
        return question, selected, note, event


class AnalystAgent(Agent):
    name = "analyst"

    def __init__(self, provider: TextProvider | None = None) -> None:
        self.provider = provider

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
        evidence_packet = "\n".join(lines)
        notes_packet = "\n\n".join(f"{question}\n{note}" for question, note in workspace.research_notes.items())
        if self.provider:
            workspace.synthesis = self.provider.complete(
                "You are a research analyst. Reconcile the research notes into a structured synthesis. Preserve source markers and identify uncertainty.",
                f"Topic: {workspace.topic}\n\nResearch notes:\n{notes_packet}\n\nEvidence:\n{evidence_packet}",
            )
        else:
            workspace.synthesis = evidence_packet
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
                request += "\n\nPrevious draft:\n" + workspace.draft
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

    def __init__(self, provider: TextProvider | None = None) -> None:
        self.provider = provider

    def run(self, workspace: Workspace) -> list[str]:
        started = time.perf_counter()
        known = {item.source_id for values in workspace.evidence.values() for item in values}
        cited = set(re.findall(r"\[(S\d+)\]", workspace.draft))
        notes = []
        unknown = cited - known
        if unknown:
            notes.append("Remove unknown citations: " + ", ".join(sorted(unknown)))
        if not cited and known:
            notes.append("Add source markers to factual claims.")
        if self.provider:
            semantic = self.provider.complete(
                "You are a strict research critic. Check whether the report answers the question, stays within the evidence, and states limitations. Return PASS or one concise issue per line.",
                f"Question: {workspace.topic}\n\nOriginal excerpts:\n" + "\n".join(
                    f"[{e.source_id}] {e.excerpt}" for items in workspace.evidence.values() for e in items
                ) + f"\n\nReport:\n{workspace.draft}",
            )
            if semantic.strip().upper() != "PASS":
                notes.extend(line.lstrip("-* ").strip() for line in semantic.splitlines() if line.strip())
        workspace.critique = notes
        self.record(workspace, started, "audited citations", issues=len(notes))
        return notes
