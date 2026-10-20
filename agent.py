"""One agent definition and one bounded SDK run."""

from agents import Agent, RunConfig, RunResult, Runner

from mock_model import MockResearchModel
from tools import ResearchState, read_company_page, search_company


def build_agent(verbose: bool = True) -> Agent[ResearchState]:
    return Agent[ResearchState](
        name="Company Research Agent",
        instructions="Research the company. Use tools. Explain divisions and revenue. Cite sources.",
        model=MockResearchModel(verbose=verbose),
        tools=[search_company, read_company_page],
    )


async def research(state: ResearchState) -> RunResult:
    if not state.company.strip():
        raise ValueError("Company name must not be empty.")
    return await Runner.run(
        build_agent(verbose=state.verbose),
        input=state.company,
        context=state,
        max_turns=4,
        run_config=RunConfig(tracing_disabled=True),
    )
