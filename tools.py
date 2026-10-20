"""Local practice data and tools. No websites are contacted."""

import json
from dataclasses import dataclass, field

from agents import RunContextWrapper, function_tool

MOCK_URL = "mock://siemens-energy/businesses"
MOCK_PAGE = {
    "kind": "page",
    "url": MOCK_URL,
    "title": "Siemens Energy practice fixture",
    "mock": True,
    "divisions": [
        {"name": "Gas Services", "function": "Gas turbines and power plant services.",
         "revenue": "Equipment sales, maintenance, spare parts and service contracts."},
        {"name": "Grid Technologies", "function": "Equipment for electricity transmission.",
         "revenue": "Grid equipment, project delivery and related services."},
        {"name": "Transformation of Industry", "function": "Energy equipment for industry.",
         "revenue": "Industrial equipment sales, engineering and maintenance."},
        {"name": "Siemens Gamesa", "function": "Wind turbines and wind farm services.",
         "revenue": "Turbine sales, installation and long-term service contracts."},
    ],
}


@dataclass
class ResearchState:
    """Application memory for one run; separate from model conversation history."""

    company: str
    verbose: bool = True
    searches: list[str] = field(default_factory=list)
    pages_read: list[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        if self.verbose:
            print(message)


@function_tool
def search_company(ctx: RunContextWrapper[ResearchState], company: str) -> str:
    """Search local mock company records; return source identifiers."""
    ctx.context.searches.append(company)
    results = []
    if company.strip().casefold() == "siemens energy":
        results = [{"title": MOCK_PAGE["title"], "url": MOCK_URL}]
    ctx.context.log(f"TOOL search_company({company!r}) -> {len(results)} result(s)")
    ctx.context.log(f"STATE searches={len(ctx.context.searches)}, pages={len(ctx.context.pages_read)}")
    return json.dumps({"kind": "search", "mock": True, "results": results})


@function_tool
def read_company_page(ctx: RunContextWrapper[ResearchState], url: str) -> str:
    """Read a local mock page; never fetch a URL from the internet."""
    if url != MOCK_URL:
        ctx.context.log(f"TOOL read_company_page({url!r}) -> unknown source")
        return json.dumps({"kind": "error", "error": "Unknown mock source."})
    ctx.context.pages_read.append(url)
    ctx.context.log(f"TOOL read_company_page({url!r}) -> practice division data")
    ctx.context.log(f"STATE searches={len(ctx.context.searches)}, pages={len(ctx.context.pages_read)}")
    return json.dumps(MOCK_PAGE)

