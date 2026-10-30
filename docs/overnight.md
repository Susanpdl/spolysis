# Overnight work with GNHF

The main checkout is a standalone repository at `/Users/spoudel/Desktop/spolysis`.
Its `origin` is `https://github.com/Susanpdl/spolysis.git`.
The original Desktop-layout history is preserved on `archive/desktop-layout` on GitHub and in `.git/desktop-repository-backup` locally.
Do not restore the Desktop repository metadata over the standalone repository.

## Local preparation

GNHF is installed globally and uses the authenticated Codex CLI.
Its machine-local configuration is `~/.gnhf/config.yml`.
The configuration selects `workspace-write`, permits network access, disables interactive approval prompts, prevents sleep, and stops after three consecutive failures.
Commands outside the sandbox's permitted scope can fail rather than wait for an unattended approval.
Do not replace this configuration with GNHF's default permission bypass.

The prepared worktree is `.worktrees/overnight`, on branch `overnight/prepared`.
It has its own app dependencies and Python test environment.
No production environment files are copied into it.
Keep the Mac powered on with its lid open and connected to power during the run.

Before launching, agree on a concrete objective, observable stop condition, iteration cap, and token cap.
GNHF counts cached context tokens toward its token cap, so a small output can still consume a substantial part of that cap.
The installed CLI has no wall-clock deadline flag; a strict deadline requires a separately agreed stop mechanism.
Run one worker, keep its commits local, and review the result before merging.

```sh
cd /Users/spoudel/Desktop/spolysis/.worktrees/overnight
git status --short --branch
git log -3 --oneline
# Replace each placeholder with the agreed task and limits before running.
gnhf --agent codex --current-branch \
  --max-iterations ITERATION_CAP \
  --max-tokens TOKEN_CAP \
  --stop-when 'OBSERVABLE_COMPLETION_CONDITION' \
  'OBJECTIVE_AND_CONSTRAINTS'
```

Use `--current-branch` inside this already isolated worktree.
Do not add `--push` unless the user authorizes pushing the overnight run.
GNHF's own `--worktree` flag creates a sibling directory outside this workspace; do not combine it with `--current-branch`.

## Verification and review

Run the checks in [README.md](../README.md) from the worktree.
Follow [AGENTS.md](../AGENTS.md) and [CLAUDE.md](../CLAUDE.md).
Use fixture-backed tests without production credentials; these do not establish production readiness or model accuracy.

GNHF saves prompts, iteration output, notes, logs, and `end-state.json` under the worktree's `.gnhf/runs/` directory.
Read those records, inspect the commits and diff, and independently rerun relevant checks before accepting its completion claim.
Use Ctrl+C once to request a graceful stop and let the current iteration finish.
A second Ctrl+C or SIGTERM force-stops the run.
