"""Run the existing mock agent and grade observable behavior, without network access."""

import argparse
import asyncio
from contextlib import ExitStack
from dataclasses import asdict, dataclass
from importlib.metadata import version
import json
from pathlib import Path
import sys
from typing import TypedDict
from unittest.mock import patch

from agent import research
from evals.cases import CASES, EvalCase
from tools import ResearchState


@dataclass(frozen=True)
class Observation:
    report: str = ""
    tools: tuple[str, ...] = ()
    turns: int = 0
    error: str | None = None


class CaseResult(TypedDict):
    name: str
    company: str
    passed: bool
    checks: dict[str, bool]
    observation: dict[str, object]


class Summary(TypedDict):
    suite: str
    mode: str
    sdk_version: str
    limitation: str
    passed: int
    total: int
    results: list[CaseResult]


def grade(case: EvalCase, observation: Observation) -> dict[str, bool]:
    """Simple text checks are regression signals, not semantic fact verification."""
    report = observation.report.casefold()
    return {
        "expected_outcome": observation.error == case.expected_error,
        "required_content": all(text.casefold() in report for text in case.required_text),
        "forbidden_content_absent": all(
            text.casefold() not in report for text in case.forbidden_text
        ),
        "tool_sequence": observation.tools == case.expected_tools,
        "turn_limit": 0 <= observation.turns <= case.max_turns,
        "report_on_success_only": bool(observation.report.strip()) == (case.expected_error is None),
    }


async def observe(case: EvalCase) -> Observation:
    state = ResearchState(company=case.company, verbose=False)
    try:
        result = await research(state, live=False)
    except ValueError:
        # A rejected input must not have executed research tools before failing.
        calls = tuple("search_company" for _ in state.searches) + tuple(
            "read_company_page" for _ in state.pages_read
        )
        return Observation(tools=calls, error="ValueError")
    calls = tuple(
        item["name"] for item in result.to_input_list()
        if item.get("type") == "function_call"
    )
    return Observation(report=result.final_output, tools=calls, turns=len(result.raw_responses))


async def evaluate() -> Summary:
    """Block network attempts for the entire suite, even if agent defaults change."""
    results: list[CaseResult] = []
    with ExitStack() as stack:
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.getaddrinfo"):
            stack.enter_context(patch(target, side_effect=RuntimeError("Evaluation network forbidden")))
        for case in CASES:
            try:
                observation = await observe(case)
            except Exception as error:
                # Keep grading other cases. Never persist potentially sensitive exception messages.
                observation = Observation(error=type(error).__name__)
            checks = grade(case, observation)
            results.append({
                "name": case.name, "company": case.company,
                "passed": all(checks.values()), "checks": checks,
                "observation": asdict(observation),
            })
    return {
        "suite": "offline-v1", "mode": "scripted-mock",
        "sdk_version": version("openai-agents"),
        "limitation": "Regression checks only; no real-model quality or independent fact verification.",
        "passed": sum(bool(result["passed"]) for result in results),
        "total": len(results), "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write the current result as UTF-8 JSON")
    args = parser.parse_args()
    summary = asyncio.run(evaluate())
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        failed = [name for name, passed in result["checks"].items() if not passed]
        detail = f" (failed: {', '.join(failed)})" if failed else ""
        print(f"{status} {result['name']}{detail}")
    print(f"Offline baseline: {summary['passed']}/{summary['total']} cases passed.")
    print(summary["limitation"])
    if args.output is not None:
        try:
            args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        except OSError:
            print("Could not write evaluation output. Check the destination directory.", file=sys.stderr)
            return 1
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
