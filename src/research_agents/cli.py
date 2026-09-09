import argparse
import json
import os
from pathlib import Path

from .length_model import LengthModel
from .models import Source
from .orchestrator import ResearchOrchestrator, save_report
from .provider import OpenAICompatibleProvider
from .scheduling import estimate_length


def load_sources(path: Path) -> list[Source]:
    records = json.loads(path.read_text(encoding="utf-8"))
    return [Source(**record) for record in records]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small multi-agent research workflow.")
    parser.add_argument("topic")
    parser.add_argument("--sources", type=Path, default=Path("examples/sources.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/report.md"))
    parser.add_argument("--live", action="store_true", help="Use an OpenAI-compatible chat-completions API.")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent researcher slots, not GPU count.")
    parser.add_argument("--policy", choices=("fcfs", "sjf"), default="fcfs")
    parser.add_argument("--length-model", type=Path, help="Optional model created by research_agents.length_model.")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    if args.live and "LLM_API_KEY" not in os.environ:
        parser.error("--live requires LLM_API_KEY")
    provider = OpenAICompatibleProvider() if args.live else None
    length_model = LengthModel.load(args.length_model) if args.length_model else None
    workspace = ResearchOrchestrator(
        provider=provider,
        workers=args.workers,
        policy=args.policy,
        length_estimator=length_model.estimate if length_model else estimate_length,
        estimator_name=length_model.method if length_model else "rule-baseline",
    ).run(args.topic, load_sources(args.sources))
    save_report(workspace, args.output)
    if provider:
        args.output.with_suffix(".calls.json").write_text(json.dumps(provider.calls, indent=2), encoding="utf-8")
    print(f"Saved report to {args.output}")
    print("Agents: " + " -> ".join(event.agent for event in workspace.events))


if __name__ == "__main__":
    main()
