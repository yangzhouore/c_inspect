# MVP 2: company web search

## Plan
1. Add an opt-in company-domain web mode to the existing single agent.
2. Use the SDK hosted web-search tool; preserve both existing mock modes.
3. Render API citation URLs inline and withhold unsupported reports.
4. Test the SDK request, output handling, and failures without network access.
5. Validate locally and in GitHub CI; commit on a separate MVP branch.
6. Open a PR for manual review and leave it unmerged.

## Applicability review
- Confirmed: one Agent/Runner, a pinned SDK, two mock tools, and existing CI.
- Confirmed: no dependencies, database, or multi-agent system are needed.
- Inference: a user-supplied company domain is the smallest useful search scope.
- Open question before research: SDK/model support for domain-filtered search.
- Decision after research: supported; use `--live --web-domain company.com`.
- Search runs on OpenAI's service, unlike locally executed function tools.
- Sources are company-published evidence, not independently verified claims.

## Research
The installed SDK supports `WebSearchTool.filters` and `external_web_access`.
The Responses API supports domain filters, citations, and `gpt-4.1-mini` search.
Domain filtering includes subdomains. API citation metadata provides URLs.
Reference: https://developers.openai.com/api/docs/guides/tools-web-search

## Acceptance checks
- No web/API access by default; explicit live mode and a domain are required.
- Domain filters are serialized in the real SDK's Responses API request.
- A completed hosted action and in-domain citation metadata are required.
- Invalid domains, missing evidence, and API errors fail without a report.
- Existing tests pass; new cases run in CI on Python 3.12 and 3.14.
- Live account/model behavior needs a configured replacement API key.

## Scope
No custom crawler, source database, or independent claim-verification stage.
Limit hosted tool calls to three per API response and SDK turns to four.
Neither limit is a total spending cap. CI uses simulated API responses.

## Local validation
All 25 tests pass, including SDK serialization and inline citation handling.
Dependency checks pass. Existing offline CLI examples still run successfully.
No live API request was made; no replacement credential is configured.
