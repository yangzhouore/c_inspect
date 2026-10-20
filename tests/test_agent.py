"""Exercise the actual SDK loop with network access forbidden."""

import os
import unittest
from unittest.mock import patch

from agents import RunConfig, Runner
from agents.exceptions import MaxTurnsExceeded

from agent import build_agent, research
from tools import MOCK_URL, ResearchState, read_company_page


class ResearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.network = patch("socket.socket.connect", side_effect=AssertionError("Network forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    async def test_sdk_loop_calls_tools_and_carries_results(self) -> None:
        state = ResearchState("Siemens Energy", verbose=False)
        result = await research(state)
        history = result.to_input_list()
        calls = [item for item in history if item.get("type") == "function_call"]
        outputs = [item for item in history if item.get("type") == "function_call_output"]
        self.assertEqual([call["name"] for call in calls], ["search_company", "read_company_page"])
        self.assertEqual([call["call_id"] for call in calls], [item["call_id"] for item in outputs])
        self.assertEqual(len(result.raw_responses), 3)
        self.assertEqual(state.searches, ["Siemens Energy"])
        self.assertEqual(state.pages_read, [MOCK_URL])
        for name in ("Gas Services", "Grid Technologies", "Transformation of Industry", "Siemens Gamesa"):
            self.assertIn(name, result.final_output)
        self.assertIn("not verified", result.final_output)
        self.assertIn(MOCK_URL, result.final_output)

    async def test_unknown_company_stops_without_reading_or_inventing(self) -> None:
        state = ResearchState("Unknown Company", verbose=False)
        result = await research(state)
        self.assertEqual(len(result.raw_responses), 2)
        self.assertEqual(state.pages_read, [])
        self.assertIn("No local data", result.final_output)
        self.assertNotIn("Gas Services", result.final_output)

    async def test_runs_do_not_share_state(self) -> None:
        first = ResearchState("Siemens Energy", verbose=False)
        second = ResearchState("Siemens Energy", verbose=False)
        agent = build_agent(verbose=False)
        for state in (first, second):
            await Runner.run(agent, input=state.company, context=state,
                             run_config=RunConfig(tracing_disabled=True), max_turns=4)
        self.assertEqual(first.pages_read, [MOCK_URL])
        self.assertEqual(second.pages_read, [MOCK_URL])
        self.assertIsNot(first.pages_read, second.pages_read)

    async def test_turn_limit_stops_the_loop(self) -> None:
        state = ResearchState("Siemens Energy", verbose=False)
        with self.assertRaises(MaxTurnsExceeded):
            await Runner.run(build_agent(False), input=state.company, context=state,
                             max_turns=1, run_config=RunConfig(tracing_disabled=True))

    async def test_empty_company_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            await research(ResearchState("  ", verbose=False))

    async def test_unknown_source_returns_explicit_error(self) -> None:
        from agents.tool_context import ToolContext
        import json
        state = ResearchState("Siemens Energy", verbose=False)
        output = await read_company_page.on_invoke_tool(
            ToolContext(context=state, tool_name="read_company_page", tool_call_id="test-call", tool_arguments=json.dumps({"url": "mock://unknown"})), json.dumps({"url": "mock://unknown"}))
        self.assertEqual(json.loads(output)["kind"], "error")
        self.assertEqual(state.pages_read, [])


if __name__ == "__main__":
    unittest.main()

