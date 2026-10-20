"""Run the local learning prototype: python main.py [company]."""

import argparse
import asyncio
import sys

from agents.exceptions import AgentsException

from agent import research
from tools import ResearchState


async def main() -> int:
    parser = argparse.ArgumentParser(description="Offline company research learning demo")
    parser.add_argument("company", nargs="?", default="Siemens Energy")
    args = parser.parse_args()
    state = ResearchState(company=args.company)
    try:
        result = await research(state)
    except (AgentsException, ValueError) as error:
        print(f"Research failed: {error}", file=sys.stderr)
        return 1
    print(f"\n{result.final_output}")
    print(f"Model turns: {len(result.raw_responses)}; tool calls: {len(state.searches) + len(state.pages_read)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
