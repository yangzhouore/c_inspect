"""Ensure evaluation rules catch regressions instead of always reporting success."""

import asyncio
from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from evals.cases import CASES, KNOWN_COMPANY
from evals.run import Observation, evaluate, grade, main, observe
from tools import ResearchState


class EvaluationTests(unittest.TestCase):
    def test_rules_reject_missing_evidence_wrong_tools_and_excess_turns(self) -> None:
        good = Observation(
            report="\n".join(KNOWN_COMPANY.required_text),
            tools=KNOWN_COMPANY.expected_tools, turns=3,
        )
        self.assertTrue(all(grade(KNOWN_COMPANY, good).values()))
        bad = replace(good, report=good.report.replace("mock://siemens-energy/businesses", ""))
        self.assertFalse(grade(KNOWN_COMPANY, bad)["required_content"])
        bad = replace(good, report=good.report + " https://invented.example")
        self.assertFalse(grade(KNOWN_COMPANY, bad)["forbidden_content_absent"])
        self.assertFalse(grade(KNOWN_COMPANY, replace(good, tools=()))["tool_sequence"])
        self.assertFalse(grade(KNOWN_COMPANY, replace(good, turns=5))["turn_limit"])

    def test_unknown_company_cannot_pass_with_invented_divisions(self) -> None:
        case = next(case for case in CASES if case.name == "unknown_company")
        bad = Observation("No local data. Gas Services", ("search_company",), 2)
        self.assertFalse(grade(case, bad)["forbidden_content_absent"])

    def test_expected_rejection_is_not_any_exception(self) -> None:
        blank = next(case for case in CASES if case.name == "blank_input")
        self.assertTrue(all(grade(blank, Observation(error="ValueError")).values()))
        self.assertFalse(grade(blank, Observation(error="RuntimeError"))["expected_outcome"])
        self.assertFalse(grade(blank, Observation())["expected_outcome"])

    def test_rejection_after_tool_execution_cannot_pass_as_early_validation(self) -> None:
        async def late_rejection(state: ResearchState, *, live: bool) -> None:
            state.searches.append(state.company)
            raise ValueError("Rejected too late")

        blank = next(case for case in CASES if case.name == "blank_input")
        with patch("evals.run.research", side_effect=late_rejection):
            observation = asyncio.run(observe(blank))
        self.assertFalse(grade(blank, observation)["tool_sequence"])

    def test_suite_blocks_network_and_records_failures_without_raw_errors(self) -> None:
        async def attempt_network(case: object) -> Observation:
            socket.getaddrinfo("example.com", 443)
            raise AssertionError("Network should have been blocked")

        with patch("evals.run.observe", side_effect=attempt_network):
            summary = asyncio.run(evaluate())
        self.assertEqual(summary["passed"], 0)
        self.assertEqual(len(summary["results"]), len(CASES))
        for result in summary["results"]:
            self.assertEqual(result["observation"]["error"], "RuntimeError")
        self.assertNotIn("Evaluation network forbidden", json.dumps(summary))

    def test_cli_writes_baseline_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "baseline.json"
            with patch.dict("os.environ", {}, clear=True), redirect_stdout(io.StringIO()):
                with patch("sys.argv", ["evals.run", "--output", str(output)]):
                    self.assertEqual(main(), 0)
            summary = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(summary["passed"], len(CASES))
        self.assertEqual(summary["mode"], "scripted-mock")
        self.assertEqual(len(summary["results"]), len(CASES))

    def test_cli_returns_failure_when_case_fails_or_output_cannot_be_written(self) -> None:
        with patch("evals.run.observe", side_effect=RuntimeError("Do not disclose this")):
            with patch("sys.argv", ["evals.run"]), redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(main(), 1)
        self.assertIn("FAIL known_company", stdout.getvalue())
        self.assertNotIn("Do not disclose this", stdout.getvalue())
        with tempfile.TemporaryDirectory() as directory:
            with patch("sys.argv", ["evals.run", "--output", directory]):
                with redirect_stdout(io.StringIO()), patch("sys.stderr", new_callable=io.StringIO):
                    self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
