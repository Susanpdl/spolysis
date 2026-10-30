# Agent instructions

Read [CLAUDE.md](CLAUDE.md) for shared project context and engineering constraints.
Use [README.md](README.md) for setup and checks, and [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md) for recorded validation and release blockers.
Proposals in [v2.md](v2.md) require the user's choice before implementation.

- Never use the em dash character; use a plain dash.
- Never add an agent co-author to commit messages.
- Never manually modify CHANGELOG.md or generated files.
- In long Markdown files, put each complete sentence on its own line while preserving normal Markdown structure.
- Prefer quality, simplicity, robustness, scalability, and maintainability over development cost.
- For one-off operations, start with the simplest direct end-to-end path; add machinery only for concrete blockers or repeated needs.
- Reproduce bugs through the end-user workflow before fixing them.
- During end-to-end testing, fix clearly incorrect UI, lint failures, test failures, and flakiness encountered along the way.
- Explain tradeoffs and obtain explicit approval before using a harness feature that launches a large swarm of agents.
- If a materially better structural fix exists, disclose it with a recommendation rather than silently adding a workaround.
  For routine decisions, explain briefly and proceed with the sensible default.
  For large structural changes, present options and wait for the user's choice.

## Local verification

Use Python 3.11 for the pinned CPU test dependencies in [requirements-dev.txt](requirements-dev.txt).
The local test environment is `.venv-test`; the existing `.venv` is separate.
Run `.venv-test/bin/python -m pytest -q` and `.venv-test/bin/python -m ruff check api pipeline tests` from the repository root.
Run the app checks listed in README after app changes.
Each worktree needs its own dependency installation; do not share mutable node_modules directories.

## Overnight work

Use one isolated worktree and an explicit objective, stop condition, iteration cap, and token cap.
Do not start an overnight run until the user has supplied its objective and limits.
Keep commits local unless the user authorizes pushing that run.
Do not deploy, change production data, or make unapproved product or architecture decisions.
Leave progress, verification results, and blockers in GNHF's run notes.
Preserve user changes and never claim completion without relevant verification.

## Maintaining this file

Keep only concise knowledge useful to almost every future session.
Point to authoritative files or commands instead of repeating the codebase.
Prefer rewriting or pruning entries over appending new ones.
