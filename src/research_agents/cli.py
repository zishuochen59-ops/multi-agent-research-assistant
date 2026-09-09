import argparse
import json
import os
from pathlib import Path

from .models import Source
from .orchestrator import ResearchOrchestrator, save_report
from .provider import OpenAICompatibleProvider


def load_sources(path: Path) -> list[Source]:
    records = json.loads(path.read_text(encoding="utf-8"))
    return [Source(**record) for record in records]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small multi-agent research workflow.")
    parser.add_argument("topic")
    parser.add_argument("--sources", type=Path, default=Path("examples/sources.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/report.md"))
    parser.add_argument("--live", action="store_true", help="Use an OpenAI-compatible chat-completions API.")
    args = parser.parse_args()
    if args.live and "LLM_API_KEY" not in os.environ:
        parser.error("--live requires LLM_API_KEY")
    provider = OpenAICompatibleProvider() if args.live else None
    workspace = ResearchOrchestrator(provider=provider).run(args.topic, load_sources(args.sources))
    save_report(workspace, args.output)
    print(f"Saved report to {args.output}")
    print("Agents: " + " -> ".join(event.agent for event in workspace.events))


if __name__ == "__main__":
    main()
