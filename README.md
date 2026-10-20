# Company Research Agent: company-domain web search

One agent explains company divisions and how they earn revenue.
The default mode is offline; `--live` uses an OpenAI model to choose tools.
Without `--web-domain`, both modes use the local Siemens Energy fixture.
Mock reports are practice data; `mock://` identifiers are not public citations.

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

Live mode sends company input and tool results to OpenAI and uses API credits.
Web mode also incurs search charges. Tracing uploads are disabled in all modes.
The default model is `gpt-4.1-mini`; choose another accessible model with:

```powershell
.\.venv\Scripts\python.exe main.py "Siemens Energy" --live --model gpt-4.1
```

The program reads `OPENAI_API_KEY` from the environment. It does not load `.env`
files. `.gitignore` excludes `.env` and `.env.*` if you keep local credentials
there yourself. Never force-add credential files or put keys in source code.
Missing credentials and API failures return exit code 1 without raw API errors.

## Agent loop

`main.py` -> `agent.py` -> SDK Runner -> model -> tools
The model requests tools; the SDK executes local functions and returns results.
Offline mode scripts search -> read -> report in three turns and two calls.
Live mock mode chooses tools from instructions; its behavior can vary.
`CALL`, `TOOL`, and `STATE` logs expose actions, execution, and local memory.
ResearchState is per-run tool context; it is not sent to the model automatically.
The mock model in `mock_model.py` uses conversation history, not a turn counter.

## Company web research (MVP 2)

With `OPENAI_API_KEY` configured in the shell, use a company-controlled domain:

```powershell
.\.venv\Scripts\python.exe main.py "Siemens Energy" --live --web-domain siemens-energy.com
```

The agent uses hosted web search restricted to that domain and its subdomains.
Supply a bare domain without `https://` or a path. The app cannot establish that
it belongs to the company; choose it carefully. No mock tools run in web mode.
OpenAI executes hosted actions inside the model request. `HOSTED` logs show
returned action/status metadata, and the summary counts completed actions.
Limits: three hosted tool calls per response and four SDK turns, not a cost cap.

Inline links come from API citation annotations. Missing completed searches,
missing citations, or citations outside the domain cause exit code 1 and no
report. This is basic evidence handling, not independent claim verification.
Company statements may be incomplete or outdated. No match may yield no report.
The plan and applicability review are in [docs/mvp2-plan.md](docs/mvp2-plan.md).

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
required. CI includes web request/citation tests using simulated API responses.
Each MVP belongs on its own branch and an unmerged PR for manual review.

Live API behavior has not been checked without a configured replacement key.
Independent source/claim verification remains a later learning stage.
SDK reference: https://developers.openai.com/api/docs/guides/agents/sdk
