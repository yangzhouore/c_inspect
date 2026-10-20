# Company Research Agent: first local prototype

Learn the OpenAI Agents SDK without an API key. All decisions and data are mocks.
No OpenAI requests, web searches or tracing uploads happen during a run.
The sample report is practice data, not current or verified company research.
Its `mock://` references are local identifiers, not reliable public citations.

## Run

From this project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe main.py "Unknown Company"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The only direct dependency is `openai-agents`. Python 3.14 was used locally.

## Minimal architecture

`main.py` -> `agent.py` -> SDK Runner -> `mock_model.py` -> `tools.py`

- `main.py`: accepts a company name and prints the result.
- `agent.py`: defines one Agent, its tools and a bounded run.
- `mock_model.py`: replaces an LLM with explicit rules.
- `tools.py`: supplies mock search/page data and the ResearchState dataclass.

An Agent combines instructions, a decision model and available tools.
A tool is a function the model can request by name with JSON arguments.
The SDK validates arguments and executes the registered function.
The mock model emits SDK-compatible responses; it never executes tools itself.
The short agent instructions are for a future LLM; the mock follows Python rules.

## Watch the loop

1. No tool result exists: request `search_company` with the company name.
2. The SDK executes search and adds its result to conversation history.
3. A source exists: request `read_company_page` with the returned identifier.
4. The SDK executes read and adds the page to conversation history.
5. Division data exists: return a final report. The SDK stops.

A normal run makes three model decisions and two tool calls.
An unknown company stops after search, without inventing a report.
`max_turns=4` bounds model turns, not the number of tools.
Printed DECISION messages explain scripted rules, not hidden LLM reasoning.
CALL messages show the requested tool and its JSON arguments.
TOOL and STATE messages show execution and application memory changes.

## Two kinds of state

Conversation history contains user input, tool calls and tool outputs.
The SDK passes this history to the model on each turn.
`result.to_input_list()` exposes it after the run.
Call IDs connect each tool request to its returned output.

ResearchState holds the company, search queries and pages successfully read.
The SDK passes it to tools through RunContextWrapper.
This local context is not automatically sent to the model.
Each new run gets fresh state; nothing is stored on disk.
The mock selects its next action from history, not a hidden turn counter.

## Try a small experiment

Change one revenue description in MOCK_PAGE, then run again.
The final report changes because the model reads the tool output.
Run an unknown company to see the no-data stopping decision.

## Later: a real model

Replace MockResearchModel in build_agent with an SDK-supported real model.
The Runner, tool contracts and state pattern can stay.
Mock tools must also be replaced before doing actual website research.
Credential setup, live search and source verification are future steps.

SDK reference: https://developers.openai.com/api/docs/guides/agents/sdk
