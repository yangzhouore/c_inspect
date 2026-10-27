"""Handwritten expectations, kept separate from the agent's practice data."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalCase:
    name: str
    company: str
    required_text: tuple[str, ...]
    forbidden_text: tuple[str, ...]
    expected_tools: tuple[str, ...]
    max_turns: int
    expected_error: str | None = None


KNOWN_COMPANY = EvalCase(
    name="known_company",
    company="Siemens Energy",
    required_text=(
        "not verified company research",
        "Gas Services", "Gas turbines", "spare parts",
        "Grid Technologies", "electricity transmission", "project delivery",
        "Transformation of Industry", "Energy equipment for industry", "engineering",
        "Siemens Gamesa", "Wind turbines", "long-term service contracts",
        "mock://siemens-energy/businesses",
    ),
    forbidden_text=("https://", "http://"),
    expected_tools=("search_company", "read_company_page"),
    max_turns=3,
)

CASES = (
    KNOWN_COMPANY,
    EvalCase(
        name="normalized_company", company="  sIeMeNs EnErGy  ",
        required_text=KNOWN_COMPANY.required_text,
        forbidden_text=KNOWN_COMPANY.forbidden_text,
        expected_tools=KNOWN_COMPANY.expected_tools, max_turns=3,
    ),
    EvalCase(
        name="unknown_company", company="Unknown Company",
        required_text=("No local data",),
        forbidden_text=("Gas Services", "Grid Technologies", "Makes money through:",
                        "Mock source:", "https://", "http://"),
        expected_tools=("search_company",), max_turns=2,
    ),
    EvalCase(
        name="blank_input", company="   ", required_text=(), forbidden_text=(),
        expected_tools=(), max_turns=0, expected_error="ValueError",
    ),
)
