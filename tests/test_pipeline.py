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
        _, evidence, _ = RetrievalAgent(1).run("How does scheduling improve resource allocation?", [source])
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


if __name__ == "__main__":
    unittest.main()
