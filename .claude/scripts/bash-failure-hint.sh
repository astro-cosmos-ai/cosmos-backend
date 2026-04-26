#!/usr/bin/env bash
# PostToolUseFailure hook for Bash: surface common recovery hints.
set -e

input=$(cat)
cmd=$(echo "$input" | jq -r '.tool_input.command // empty')
err=$(echo "$input" | jq -r '.error // empty')

hint=""

case "$cmd" in
  *"uv run pytest"*)
    hint="pytest failed. Read the assertion + traceback before editing — if expected value was hand-rolled, recompute it manually. Consider delegating to the debugger subagent."
    ;;
  *"uv run uvicorn"*)
    hint="uvicorn failed to start. Check .env keys are set, that port 8000 is free (lsof -i :8000), and that uv sync has been run. /run-backend does an env preflight."
    ;;
  *"uv sync"*)
    hint="uv sync failed. Confirm pyproject.toml is valid and Python 3.12+ is active (cat .python-version)."
    ;;
  *"uv run python"*registry*)
    hint="Registry import failed. Likely a missing prompt module, a typo in app/agents/registry.py imports, or VALID_SECTIONS out of sync."
    ;;
  *"uv run python"*)
    hint="Python invocation failed. If ImportError, check that you're running via 'uv run' (not bare python) so the virtualenv is loaded."
    ;;
esac

if [ -z "$hint" ]; then
  case "$err" in
    *"permission denied"*|*"Permission denied"*)
      hint="Permission denied. Don't sudo — check file ownership or whether the path is sandboxed."
      ;;
    *"address already in use"*|*"Address already in use"*)
      hint="Port already in use. Find the process with: lsof -i :<port>, then stop it before retrying."
      ;;
  esac
fi

if [ -n "$hint" ]; then
  jq -n --arg h "$hint" '{systemMessage:$h}'
else
  echo '{}'
fi
