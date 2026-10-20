# AGENTS.md

## 1. Project Goal
Build a Personal Company Research Agent using Python and OpenAI Agents SDK.

The project is both a practical application and a learning exercise.

## 2. Development Principles
- Keep solutions simple, modular, and readable.
- Build incrementally, one feature at a time.
- Prefer standard Python libraries when possible.
- Avoid unnecessary dependencies and abstractions.
- Do not add features beyond the current task.

## 3. Learning Rules
- Explain new AI Agent concepts in simple language.
- Explain why each major design decision is made.
- Keep explanations short and practical.
- Show how Agent decisions and tool calls work.
- Assume Python proficiency but beginner-level Agent knowledge.

## 4. Coding Rules
- Use Python with type hints.
- Follow clear naming conventions.
- Keep functions small and focused.
- Handle errors explicitly.
- Add simple tests for important functionality.
- Never hardcode API keys or secrets.

## 5. Documentation
- Every Markdown file must contain fewer than 100 lines.
- Keep documentation concise and easy to understand.
- Avoid repeating information across files.
- Update documentation only when necessary.

## 6. Workflow
For each development task:
1. Create a concise plan, then review and verify its applicability.
2. Research the approach before implementing the smallest working solution.
3. Work on a separate Git branch for each implementation/MVP.
4. Validate locally, commit, and run GitHub Actions tests remotely.
5. Open a PR for manual review; leave it unmerged and do not enable auto-merging.
6. Summarize what changed, validation results, and what was learned.

## 7. Restrictions
- Do not introduce multi-agent systems, MCP, or databases unless requested.
- Do not rewrite working code unnecessarily.
- Do not install dependencies without explaining why.
- Do not implement multiple learning stages at once.
- Ask before making major architectural changes.

## 8. Current Focus
Understand and implement:
- Agent
- Tools
- Agent Loop
- Tool calling

Start with a single Agent that researches publicly available company information.
