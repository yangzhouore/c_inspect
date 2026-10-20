"""One agent definition and one bounded SDK run."""

import os

from agents import Agent, Model, RunConfig, RunContextWrapper, RunHooks, RunResult, Runner
from agents.items import ModelResponse
from openai.types.responses import ResponseFunctionToolCall

from mock_model import MockResearchModel
from tools import ResearchState, read_company_page, search_company


DEFAULT_MODEL = "gpt-4.1-mini"
INSTRUCTIONS = """You are running a learning demo with simulated company data.
First call search_company with the user's company name. If no results exist,
stop and say no local data is available; do not use your own company knowledge.
Otherwise call read_company_page with a source identifier returned by search.
Use only the returned page to explain each division's function and how it earns
revenue. Cite the exact mock source identifier and clearly label the report
'MOCK DATA - not verified company research'. These are simulated references,
not public citations. If a tool returns an error, explain it and stop.
Never invent missing facts or claim to have searched the web.
"""


class ToolCallLog(RunHooks[ResearchState]):
    """Show observable model actions, without exposing hidden reasoning."""

    async def on_llm_end(
        self,
        context: RunContextWrapper[ResearchState],
        agent: Agent[ResearchState],
        response: ModelResponse,
    ) -> None:
        for item in response.output:
            if isinstance(item, ResponseFunctionToolCall):
                context.context.log(f"CALL {item.name} arguments={item.arguments}")


def build_agent(
    verbose: bool = True, *, live: bool = False, model: str = DEFAULT_MODEL,
) -> Agent[ResearchState]:
    selected_model: str | Model = MockResearchModel(verbose=verbose)
    if live:
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise ValueError("Live mode requires OPENAI_API_KEY in your environment.")
        if not model.strip():
            raise ValueError("Model name must not be empty.")
        selected_model = model.strip()
    return Agent[ResearchState](
        name="Company Research Agent",
        instructions=INSTRUCTIONS,
        model=selected_model,
        tools=[search_company, read_company_page],
    )


async def research(
    state: ResearchState, *, live: bool = False, model: str = DEFAULT_MODEL,
) -> RunResult:
    if not state.company.strip():
        raise ValueError("Company name must not be empty.")
    return await Runner.run(
        build_agent(verbose=state.verbose, live=live, model=model),
        input=state.company,
        context=state,
        max_turns=4,
        hooks=ToolCallLog() if live else None,
        run_config=RunConfig(tracing_disabled=True),
    )
