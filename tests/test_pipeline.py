import json
import tempfile
import unittest
from pathlib import Path

from research_agents.agents import CriticAgent, RetrievalAgent
from research_agents.cli import load_sources
from research_agents.models import Evidence, Source, Workspace
from research_agents.orchestrator import ResearchOrchestrator, save_report


class PipelineTests(unittest.TestCase):
    def test_retrieval_returns_matching_source(self):
        source = Source("S1", "Scheduling", "https://example.test", "Scheduling improves resource allocation for multi-agent systems.")
        _, evidence, _, _ = RetrievalAgent(1).run("How does scheduling improve resource allocation?", [source])
        self.assertEqual(evidence[0].source_id, "S1")

    def test_critic_detects_unknown_citation(self):
        workspace = Workspace(topic="test", draft="Claim [S9].")
        workspace.evidence = {"q": [Evidence("S1", "A", "u", "fact", 1.0)]}
        notes = CriticAgent().run(workspace)
        self.assertTrue(any("S9" in note for note in notes))

    def test_pipeline_creates_cited_report_and_trace(self):
        sources = [Source("S1", "Scheduling", "https://example.test", "Scheduling policies compare job completion and resource allocation metrics.")]
        workspace = ResearchOrchestrator().run("scheduling resource allocation", sources)
        self.assertIn("[S1]", workspace.draft)
        self.assertTrue(any(event.agent.startswith("researcher-") for event in workspace.events))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.md"
            save_report(workspace, output)
            self.assertIn("Agent Trace", output.read_text())

    def test_live_mode_uses_multiple_model_agents(self):
        class StubProvider:
            def __init__(self):
                self.calls = []

            def complete(self, system, user):
                self.calls.append(system)
                if "planner" in system:
                    return "What is scheduling?\nHow is duration predicted?\nWhat are the limitations?"
                if "critic" in system:
                    return "PASS"
                return "Evidence-based result [S1]"

        provider = StubProvider()
        sources = [Source("S1", "Scheduling", "https://example.test", "Scheduling predicts duration and allocates resources, but estimates can be wrong.")]
        workspace = ResearchOrchestrator(provider=provider).run("scheduling", sources)
        self.assertIn("[S1]", workspace.draft)
        self.assertGreaterEqual(len(provider.calls), 7)
        self.assertTrue(any("planner" in call for call in provider.calls))
        self.assertTrue(any("critic" in call for call in provider.calls))


if __name__ == "__main__":
    unittest.main()
