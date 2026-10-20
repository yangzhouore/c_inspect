# Company Research Agent: real model with mock tools

One agent learns the tool-calling loop using simulated company data.
The default mode is offline; `--live` uses an OpenAI model to choose tools.
Both modes use the same local Siemens Energy fixture, never live websites.
Reports are practice data. `mock://` identifiers are not public citations.

## Setup and offline run

Use Python 3.12 or newer. From this directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py "Siemens Energy"
.\.venv\Scripts\python.exe main.py "Unknown Company"
```

The only direct dependency is the pinned `openai-agents` package.
You can use the virtual environment's interpreter without activating it.

## Real-model run (step 1)

Use a replacement key if a previous key was exposed. Never paste keys in chat.
This PowerShell prompt hides input and sets a key only for this shell session:

```powershell
$secret = Read-Host "Replacement OpenAI API key" -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new("", $secret).Password
Remove-Variable secret
.\.venv\Scripts\python.exe main.py "Siemens Energy" --live
Remove-Item Env:OPENAI_API_KEY
```

Live mode sends the company name and mock tool results to OpenAI and uses API
credits. Tracing uploads are disabled in both modes. No key is logged or saved.
The default model is `gpt-4.1-mini`; choose another accessible model with:

```powershell
.\.venv\Scripts\python.exe main.py "Siemens Energy" --live --model gpt-4.1
```

The program reads `OPENAI_API_KEY` from the environment. It does not load `.env`
files. `.gitignore` excludes `.env` and `.env.*` if you keep local credentials
there yourself. Never force-add credential files or put keys in source code.
Missing credentials and API failures return exit code 1 without raw API errors.

## How the loop works

`main.py` -> `agent.py` -> SDK Runner -> model -> tools in `tools.py`

1. The model requests `search_company` with the company name.
2. The SDK executes the tool and adds its result to conversation history.
3. A matching source lets the model request `read_company_page`.
4. The SDK executes read and returns its simulated division data.
5. The model writes a report, or stops if there is no data or a tool error.

Offline mode uses Python rules in `mock_model.py`: three model turns and two
calls for Siemens Energy. Live mode follows instructions; its choices and turn
count can vary. `max_turns=4` stops a run that does not finish within four turns.
Instructions guide the real model; they do not guarantee factual correctness.
`CALL` logs show tool names and JSON arguments, not hidden model reasoning.
`TOOL` and `STATE` logs show execution and changes to application memory.

Conversation history is sent to the model on each turn; call IDs link requests
to outputs. `result.to_input_list()` exposes the history after a run.
`ResearchState` holds searches and successfully read pages for one run.
The SDK passes it to tools through `RunContextWrapper`; this context is not
sent to the model automatically. Each CLI invocation gets fresh state.

## Tests and GitHub CI

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests forbid network connections and use no real credentials. Live-path tests
substitute API responses at the OpenAI client boundary, exercising the actual
SDK adapter, tool execution, returned observations, and CLI error handling.
They do not establish real-model behavior or verify account/model access.

GitHub Actions runs dependency checks, tests, and offline CLI smoke checks on
Python 3.12 and 3.14 for pushes and pull requests. No GitHub API-key secret is
required. No deployment is configured for this command-line MVP.
Each MVP belongs on its own branch and an unmerged PR for manual review.

Live website research and source verification remain later learning stages.
SDK reference: https://developers.openai.com/api/docs/guides/agents/sdk
