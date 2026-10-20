"""Test the real SDK adapter with API responses substituted, never a real key."""

import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from openai import APIError
from openai.resources.responses import AsyncResponses
from openai.types.responses import Response, ResponseOutputItem

from agent import DEFAULT_MODEL, build_agent, research
from main import main
from mock_model import MockResearchModel
from tools import MOCK_URL, ResearchState


def api_response(output: list[ResponseOutputItem], number: int) -> Response:
    """Wrap fixture output in the response type the real adapter consumes."""
    return Response(
        id=f"resp_test_{number}", created_at=0, model=DEFAULT_MODEL,
        object="response", output=output, parallel_tool_calls=False,
        tool_choice="auto", tools=[], status="completed",
    )


class LiveModelTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        for guard in (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-only-not-a-real-key"}, clear=True),
            patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")),
        ):
            guard.start()
            self.addCleanup(guard.stop)

    async def test_live_adapter_executes_tools_and_receives_their_outputs(self) -> None:
        fixture = MockResearchModel(verbose=False)
        outputs = [
            fixture.tool_call("search_company", {"company": "Siemens Energy"}).output,
            fixture.tool_call("read_company_page", {"url": MOCK_URL}).output,
            fixture.message("MOCK DATA - not verified company research.").output,
        ]
        state = ResearchState("Siemens Energy")
        log = io.StringIO()
        with patch.object(AsyncResponses, "create", side_effect=[
            api_response(output, i) for i, output in enumerate(outputs)
        ]) as create, redirect_stdout(log):
            result = await research(state, live=True)
        self.assertEqual(create.await_count, 3)
        requests = [call.kwargs for call in create.await_args_list]
        self.assertTrue(all(request["model"] == DEFAULT_MODEL for request in requests))
        self.assertEqual(
            {tool["name"] for tool in requests[0]["tools"]},
            {"search_company", "read_company_page"},
        )
        observations = [
            json.loads(item["output"]) for item in requests[2]["input"]
            if item.get("type") == "function_call_output"
        ]
        self.assertEqual([item["kind"] for item in observations], ["search", "page"])
        self.assertEqual(observations[-1]["divisions"][0]["name"], "Gas Services")
        self.assertEqual(state.searches, ["Siemens Energy"])
        self.assertEqual(state.pages_read, [MOCK_URL])
        self.assertIn("not verified", result.final_output)
        self.assertIn("CALL search_company arguments=", log.getvalue())
        self.assertIn("CALL read_company_page arguments=", log.getvalue())

    async def test_live_unknown_company_stops_after_search(self) -> None:
        fixture = MockResearchModel(verbose=False)
        outputs = [
            fixture.tool_call("search_company", {"company": "Unknown Company"}).output,
            fixture.message("No local data is available.").output,
        ]
        with patch.object(AsyncResponses, "create", side_effect=[
            api_response(output, i) for i, output in enumerate(outputs)
        ]) as create:
            state = ResearchState("Unknown Company", verbose=False)
            await research(state, live=True)
        self.assertEqual(create.await_count, 2)
        self.assertEqual(state.pages_read, [])

    async def test_missing_or_blank_key_fails_before_api_call(self) -> None:
        with patch.object(AsyncResponses, "create") as create:
            for value in (None, "", "  "):
                with self.subTest(value=value):
                    if value is None:
                        os.environ.pop("OPENAI_API_KEY", None)
                    else:
                        os.environ["OPENAI_API_KEY"] = value
                    with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
                        await research(ResearchState("Siemens Energy"), live=True)
            create.assert_not_called()

    async def test_model_override_and_empty_model(self) -> None:
        self.assertEqual(build_agent(live=True, model="gpt-4.1").model, "gpt-4.1")
        with self.assertRaisesRegex(ValueError, "Model name"):
            build_agent(live=True, model=" ")

    async def test_cli_reports_api_failure_without_provider_details(self) -> None:
        error = APIError("sensitive-provider-detail", request=None, body=None)
        stderr = io.StringIO()
        with patch("sys.argv", ["main.py", "--live"]), \
                patch.object(AsyncResponses, "create", side_effect=error), \
                redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            exit_code = await main()
        self.assertEqual(exit_code, 1)
        self.assertIn("OpenAI request failed", stderr.getvalue())
        self.assertNotIn("sensitive-provider-detail", stderr.getvalue())

    async def test_cli_missing_key_is_actionable(self) -> None:
        os.environ.pop("OPENAI_API_KEY")
        stderr = io.StringIO()
        with patch("sys.argv", ["main.py", "--live"]), \
                redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            self.assertEqual(await main(), 1)
        self.assertIn("OPENAI_API_KEY", stderr.getvalue())

    async def test_model_option_requires_live_mode(self) -> None:
        with patch("sys.argv", ["main.py", "--model", DEFAULT_MODEL]), \
                redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            await main()
        self.assertEqual(error.exception.code, 2)
