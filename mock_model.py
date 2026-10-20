"""A scripted SDK model: decides from tool results, without an LLM or API."""

import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from agents import Model
from agents.items import ModelResponse, TResponseInputItem, TResponseStreamEvent
from agents.usage import Usage
from openai.types.responses import (
    ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText,
)


class MockResearchModel(Model):
    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose

    def log(self, message: str) -> None:
        if self.verbose:
            print(f"DECISION (scripted): {message}")

    async def get_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        **settings: Any,
    ) -> ModelResponse:
        # The SDK appends tool outputs to input before asking for another decision.
        history = [{"role": "user", "content": input}] if isinstance(input, str) else input
        observations = [
            json.loads(item["output"])
            for item in history
            if item.get("type") == "function_call_output"
        ]
        if not observations:
            company = next(item["content"] for item in history if item.get("role") == "user")
            self.log("No sources yet. Select search_company.")
            return self.tool_call("search_company", {"company": company})

        latest = observations[-1]
        if latest["kind"] == "search":
            if not latest["results"]:
                self.log("Search returned no data. Stop without guessing.")
                return self.message("MOCK DEMO: No local data for this company. Try Siemens Energy.")
            url = latest["results"][0]["url"]
            self.log("Search found a source. Select read_company_page.")
            return self.tool_call("read_company_page", {"url": url})
        if latest["kind"] == "error":
            self.log("Tool returned an error. Stop and explain.")
            return self.message(f"MOCK DEMO: {latest['error']}")
        if latest["kind"] != "page":
            raise ValueError("Unexpected mock tool result.")

        self.log("Page has division data. Return a report and stop.")
        lines = ["MOCK DEMO - practice data, not verified company research.", ""]
        for division in latest["divisions"]:
            lines.extend([
                division["name"],
                f"  Function: {division['function']}",
                f"  Makes money through: {division['revenue']}",
                f"  Mock source: {latest['url']}",
                "",
            ])
        lines.append("Sources are simulated. Real website research and verification come later.")
        return self.message("\n".join(lines))

    def tool_call(self, name: str, arguments: dict[str, str]) -> ModelResponse:
        call_id = str(uuid4())
        if self.verbose:
            print(f"CALL {name} arguments={json.dumps(arguments)}")
        call = ResponseFunctionToolCall(
            id=call_id, call_id=call_id, type="function_call", name=name,
            arguments=json.dumps(arguments), status="completed",
        )
        return ModelResponse(output=[call], usage=Usage(), response_id=None)

    def message(self, text: str) -> ModelResponse:
        message = ResponseOutputMessage(
            id=str(uuid4()), type="message", role="assistant", status="completed",
            content=[ResponseOutputText(type="output_text", text=text, annotations=[])],
        )
        return ModelResponse(output=[message], usage=Usage(), response_id=None)

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[TResponseStreamEvent]:
        raise NotImplementedError("This prototype uses Runner.run, not streaming.")
        yield  # Makes this an async iterator, as required by the SDK interface.
