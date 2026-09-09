import json
import os
import unittest
from unittest.mock import patch

from research_agents.agents import RetrievalAgent
from research_agents.benchmark import experiment
from research_agents.models import Source
from research_agents.orchestrator import ResearchOrchestrator
from research_agents.provider import OpenAICompatibleProvider
from research_agents.scheduling import estimate_length, simulate, task_order


class SchedulingTests(unittest.TestCase):
    def test_hand_calculated_schedule(self):
        fcfs = simulate([8, 2, 1], [8, 2, 1], 1, "fcfs")
        sjf = simulate([8, 2, 1], [8, 2, 1], 1, "sjf")
        self.assertEqual(fcfs["mean_wait"], 6)
        self.assertAlmostEqual(sjf["mean_wait"], 4 / 3)
        self.assertEqual(fcfs["makespan"], sjf["makespan"])
        self.assertEqual(sjf["slot_utilization"], 1)

    def test_predictions_not_oracle_control_order(self):
        result = simulate([8, 2, 1], [1, 3, 2], 1, "sjf")
        self.assertEqual([e.task_id for e in result["events"]], [0, 2, 1])

    def test_concurrency_and_accounting(self):
        result = simulate([5, 3, 1], [5, 3, 1], 2, "fcfs")
        self.assertEqual(result["makespan"], 5)
        self.assertEqual(result["slot_utilization"], 0.9)
        self.assertEqual(result["events"][2].start, 3)

    def test_invalid_input(self):
        for args in (([], [], 1, "fcfs"), ([1], [1], 0, "fcfs"), ([1], [float("nan")], 1, "sjf"), ([1], [1], 1, "bad")):
            with self.assertRaises(ValueError):
                simulate(*args)

    def test_ties_and_reproducibility(self):
        self.assertEqual(task_order([2, 2, 1], "sjf"), [2, 0, 1])
        self.assertEqual(experiment(2, 6, 2), experiment(2, 6, 2))
        self.assertEqual(len(experiment(2, 6, 2)), 16)

    def test_length_cues_and_chinese_retrieval(self):
        self.assertGreater(estimate_length("详细比较方法").output_units, estimate_length("概述").output_units)
        _, evidence, _, _ = RetrievalAgent(1).run("多智能体任务调度", [Source("S1", "例子", "local://test", "多智能体任务调度可以协调资源。")])
        self.assertEqual(evidence[0].source_id, "S1")

    def test_pipeline_sjf_uses_limited_worker_and_keeps_duplicate_questions(self):
        class Provider:
            def __init__(self):
                self.research = []

            def complete(self, system, user):
                if "planner" in system:
                    return "Compare detailed methods\nBrief facts\nBrief facts"
                if "researcher" in system:
                    self.research.append(user.splitlines()[0])
                if "critic" in system:
                    return "PASS"
                return "fact [S1]"
        provider = Provider()
        workspace = ResearchOrchestrator(provider, workers=1, policy="sjf").run("demo", [Source("S1", "Facts", "local://test", "Brief facts compare detailed methods.")])
        self.assertIn("Brief facts", provider.research[0])
        self.assertIn("Compare", provider.research[-1])
        self.assertEqual(len(workspace.evidence), 3)
        self.assertIn("Compare", next(iter(workspace.evidence)))
        self.assertTrue(all(e.details["queue_ms"] >= 0 for e in workspace.events if e.agent.startswith("researcher")))

    def test_provider_usage_is_real_or_missing_not_estimated(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return json.dumps({"choices": [{"message": {"content": "result"}}], "usage": {"prompt_tokens": 12, "completion_tokens": 3}}).encode()
        with patch.dict(os.environ, {"LLM_API_KEY": "test-only"}), patch("urllib.request.urlopen", return_value=Response()):
            provider = OpenAICompatibleProvider()
            self.assertEqual(provider.complete("test", "input"), "result")
            self.assertEqual(provider.calls[0]["input_tokens"], 12)
            self.assertEqual(provider.calls[0]["output_tokens"], 3)


if __name__ == "__main__":
    unittest.main()
