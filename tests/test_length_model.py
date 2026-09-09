import json
import tempfile
import unittest
from pathlib import Path

from research_agents.length_model import (
    LengthModel,
    LengthObservation,
    augment_length_cues,
    evaluate,
    filter_normal_outliers,
    load_observations,
)
from research_agents.models import Source
from research_agents.orchestrator import ResearchOrchestrator


class LengthModelTests(unittest.TestCase):
    def setUp(self):
        self.observations = [
            LengthObservation("Briefly define an agent.", 28),
            LengthObservation("Give a concise definition of scheduling.", 35),
            LengthObservation("List three scheduling metrics.", 70),
            LengthObservation("Explain FCFS with an example.", 125),
            LengthObservation("Compare FCFS and SJF scheduling.", 165),
            LengthObservation("Explain prediction error and queue waiting time.", 190),
            LengthObservation("Provide a detailed scheduling comparison with examples.", 360),
            LengthObservation("Give a comprehensive analysis of multi-agent coordination and scheduling.", 440),
            LengthObservation("简要解释多智能体协作。", 40),
            LengthObservation("详细分析预测误差如何影响任务调度。", 390),
        ]

    def test_outlier_filter_and_cue_augmentation(self):
        records = [
            LengthObservation("short one", 20),
            LengthObservation("short two", 21),
            LengthObservation("bad label", 1000),
        ]
        self.assertEqual(len(filter_normal_outliers(records, z_limit=1.0)), 2)
        augmented = augment_length_cues([LengthObservation("Briefly explain FCFS.", 30)])
        self.assertTrue(any("concisely" in item.prompt.lower() for item in augmented))

    def test_fit_predict_save_and_load(self):
        model = LengthModel.fit(self.observations)
        self.assertLess(model.predict("Briefly define FCFS."), model.predict("Provide a detailed and comprehensive scheduling analysis."))
        self.assertEqual(model.estimate("Briefly define FCFS.").bucket, "short")
        metrics = evaluate(model, self.observations)
        self.assertGreaterEqual(metrics["bucket_accuracy"], 0.5)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.json"
            model.save(path)
            loaded = LengthModel.load(path)
            self.assertAlmostEqual(model.predict("Compare policies."), loaded.predict("Compare policies."))

    def test_jsonl_loader_and_orchestrator_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observations.jsonl"
            path.write_text(
                "\n".join(json.dumps({"prompt": item.prompt, "output_units": item.output_units}) for item in self.observations),
                encoding="utf-8",
            )
            loaded = load_observations(path)
        model = LengthModel.fit(loaded)
        workspace = ResearchOrchestrator(
            workers=1,
            policy="sjf",
            length_estimator=model.estimate,
            estimator_name=model.method,
        ).run("scheduling", [Source("S1", "Scheduling", "local://test", "Scheduling coordinates agent tasks.")])
        researcher_events = [event for event in workspace.events if event.agent.startswith("researcher")]
        self.assertTrue(researcher_events)
        self.assertTrue(all(event.details["length_estimator"] == model.method for event in researcher_events))


if __name__ == "__main__":
    unittest.main()
