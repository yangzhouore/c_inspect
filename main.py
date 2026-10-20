"""Run the learning prototype: python main.py [company] [--live]."""

import argparse
import asyncio
import sys

from agents.exceptions import AgentsException
from openai import APIError

from agent import DEFAULT_MODEL, research
from tools import ResearchState


async def main() -> int:
    parser = argparse.ArgumentParser(description="Company research demo using mock company data")
    parser.add_argument("company", nargs="?", default="Siemens Energy")
    parser.add_argument("--live", action="store_true", help="Use OpenAI with the existing mock tools")
    parser.add_argument("--model", help=f"OpenAI model for --live (default: {DEFAULT_MODEL})")
    args = parser.parse_args()
    if args.model is not None and not args.live:
        parser.error("--model requires --live")
    state = ResearchState(company=args.company)
    try:
        if args.live:
            print("LIVE MODEL / MOCK DATA - not verified company research.")
        result = await research(
            state, live=args.live, model=args.model if args.model is not None else DEFAULT_MODEL,
        )
    except APIError:
        # Provider messages may contain credential fragments; never print them.
        print("OpenAI request failed. Check your key, model access, quota, and connection.", file=sys.stderr)
        return 1
    except (AgentsException, ValueError) as error:
        detail = type(error).__name__ if args.live and isinstance(error, AgentsException) else str(error)
        print(f"Research failed: {detail}", file=sys.stderr)
        return 1
    print(f"\n{result.final_output}")
    print(f"Model turns: {len(result.raw_responses)}; tool calls: {len(state.searches) + len(state.pages_read)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
