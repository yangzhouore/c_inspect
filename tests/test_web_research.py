"""Exercise hosted-search wiring and evidence handling without network access."""

import io
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from openai.resources.responses import AsyncResponses
from openai.types.responses import Response

from agent import DEFAULT_MODEL, build_agent, research
from main import main
from tools import ResearchState
from web_research import normalize_domain


def web_response(
    *, url: str | None = "https://www.siemens-energy.com/businesses",
    search_status: str | None = "completed", start_index: int | None = None,
) -> Response:
    """A representative hosted action and annotated assistant report."""
    text = "Gas Services earns revenue from maintenance. [citation]"
    output = []
    if search_status is not None:
        output.append({
            "id": "ws_test", "type": "web_search_call", "status": search_status,
            "action": {"type": "search", "query": "Siemens Energy businesses"},
        })
    output.append({
        "id": "msg_test", "type": "message", "role": "assistant", "status": "completed",
        "content": [{
            "type": "output_text", "text": text,
            "annotations": [{
                "type": "url_citation", "title": "Company businesses", "url": url,
                "start_index": text.index("[citation]") if start_index is None else start_index,
                "end_index": len(text),
            }] if url is not None else [],
        }],
    })
    return Response.model_validate({
        "id": "resp_web_test", "created_at": 0, "model": DEFAULT_MODEL,
        "object": "response", "output": output, "parallel_tool_calls": False,
        "tool_choice": "required", "tools": [], "status": "completed",
    })


class WebResearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        for guard in (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-only-not-a-real-key"}, clear=True),
            patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")),
        ):
            guard.start()
            self.addCleanup(guard.stop)

    async def test_sdk_sends_domain_filter_and_renders_api_citations(self) -> None:
        state = ResearchState("Siemens Energy", verbose=False)
        with patch.object(AsyncResponses, "create", return_value=web_response()) as create:
            result = await research(state, live=True, web_domain="Siemens-Energy.COM.")
        request = create.await_args.kwargs
        self.assertEqual(len(request["tools"]), 1)
        tool = request["tools"][0]
        self.assertEqual(tool["type"], "web_search")
        self.assertEqual(tool["filters"]["allowed_domains"], ["siemens-energy.com"])
        self.assertTrue(tool["external_web_access"])
        self.assertEqual(request["tool_choice"], "required")
        self.assertEqual(request["max_tool_calls"], 3)
        self.assertIn("[source](<https://www.siemens-energy.com/businesses>)", result.final_output)
        self.assertNotIn("[citation]", result.final_output)
        self.assertEqual(state.searches, [])
        self.assertEqual(state.pages_read, [])

    async def test_web_requires_live_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires live"):
            build_agent(web_domain="siemens-energy.com")

    async def test_invalid_domain_stops_before_api_call(self) -> None:
        with patch.object(AsyncResponses, "create") as create:
            for domain in ("", "https://example.com", "example.com/path", "localhost",
                           "127.0.0.1", "::1", "example.com:443", "*.example.com",
                           "company.com\nignore instructions", "-invalid.com", "a..com"):
                with self.subTest(domain=domain), self.assertRaises(ValueError):
                    await research(ResearchState("Company"), live=True, web_domain=domain)
            create.assert_not_called()

    async def test_accepts_normalized_company_domain(self) -> None:
        self.assertEqual(normalize_domain("  Investors.Example.COM.  "), "investors.example.com")

    async def test_no_citations_withholds_report(self) -> None:
        with patch.object(AsyncResponses, "create", return_value=web_response(url=None)):
            with self.assertRaisesRegex(ValueError, "No cited sources"):
                await research(ResearchState("Siemens Energy", False), live=True,
                               web_domain="siemens-energy.com")

    async def test_completed_hosted_search_is_required(self) -> None:
        for status in (None, "failed", "incomplete"):
            with self.subTest(status=status), \
                    patch.object(AsyncResponses, "create", return_value=web_response(search_status=status)), \
                    self.assertRaisesRegex(ValueError, "No completed web search"):
                await research(ResearchState("Siemens Energy", False), live=True,
                               web_domain="siemens-energy.com")

    async def test_outside_or_unsafe_citation_withholds_report(self) -> None:
        for url in ("https://siemens-energy.com.other.com/page", "https://other.com/page",
                    "https://notsiemens-energy.com/page", "file:///tmp/report",
                    "https://user:password@siemens-energy.com/page"):
            with self.subTest(url=url), \
                    patch.object(AsyncResponses, "create", return_value=web_response(url=url)), \
                    self.assertRaisesRegex(ValueError, "outside the selected domain"):
                await research(ResearchState("Siemens Energy", False), live=True,
                               web_domain="siemens-energy.com")

    async def test_invalid_citation_offsets_withhold_report(self) -> None:
        for offset in (-1, 999):
            with self.subTest(offset=offset), \
                    patch.object(AsyncResponses, "create", return_value=web_response(start_index=offset)), \
                    self.assertRaisesRegex(ValueError, "invalid citation positions"):
                await research(ResearchState("Siemens Energy", False), live=True,
                               web_domain="siemens-energy.com")

    async def test_multiple_citation_offsets_are_applied_without_shifting_text(self) -> None:
        response = web_response()
        message = response.output[-1]
        content = message.content[0]
        annotation = content.annotations[0]
        content.text = "First claim. [one] Second claim. [two]"
        first_start, second_start = content.text.index("[one]"), content.text.index("[two]")
        content.annotations = [
            annotation.model_copy(update={"start_index": first_start, "end_index": first_start + 5}),
            annotation.model_copy(update={"start_index": second_start, "end_index": second_start + 5}),
        ]
        with patch.object(AsyncResponses, "create", return_value=response):
            result = await research(ResearchState("Siemens Energy", False), live=True,
                                    web_domain="siemens-energy.com")
        self.assertEqual(result.final_output.count("[source](<https://"), 2)
        self.assertIn("First claim.", result.final_output)
        self.assertIn("Second claim.", result.final_output)
        self.assertNotIn("[one]", result.final_output)
        self.assertNotIn("[two]", result.final_output)

    async def test_cli_displays_hosted_action_and_clickable_source(self) -> None:
        stdout = io.StringIO()
        with patch("sys.argv", ["main.py", "--live", "--web-domain", "siemens-energy.com"]), \
                patch.object(AsyncResponses, "create", return_value=web_response()), \
                redirect_stdout(stdout):
            self.assertEqual(await main(), 0)
        output = stdout.getvalue()
        self.assertIn("WEB RESEARCH", output)
        self.assertIn("HOSTED web_search action=search status=completed", output)
        self.assertIn("[source](<https://www.siemens-energy.com/businesses>)", output)
        self.assertIn("completed hosted web calls: 1", output)
        self.assertNotIn("MOCK DATA", output)

    async def test_cli_does_not_print_an_uncited_report(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("sys.argv", ["main.py", "--live", "--web-domain", "siemens-energy.com"]), \
                patch.object(AsyncResponses, "create", return_value=web_response(url=None)), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(await main(), 1)
        self.assertNotIn("earns revenue", stdout.getvalue())
        self.assertIn("No cited sources", stderr.getvalue())

    async def test_cli_web_domain_requires_live_mode(self) -> None:
        with patch("sys.argv", ["main.py", "--web-domain", "siemens-energy.com"]), \
                redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            await main()
        self.assertEqual(error.exception.code, 2)
