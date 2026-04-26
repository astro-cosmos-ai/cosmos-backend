#!/usr/bin/env bash
# Stop hook: nudge to commit + run tests when work seems done.
# Reads JSON on stdin, emits JSON to stdout. Never blocks.
set -e

input=$(cat)
cwd=$(echo "$input" | jq -r '.cwd // empty')
if [ -n "$cwd" ]; then
  cd "$cwd" 2>/dev/null || true
fi

reminders=""
nl=$'\n'

# Uncommitted changes?
if git rev-parse --git-dir >/dev/null 2>&1; then
  dirty=$(git status --porcelain | wc -l | tr -d ' ')
  if [ "$dirty" != "0" ]; then
    reminders="${reminders}${nl}- ${dirty} uncommitted change(s) in working tree. Stage + commit when this unit of work is logically complete."
  fi
fi

# Python edits without a test run?
if [ -d tests ] && git rev-parse --git-dir >/dev/null 2>&1; then
  changed_py=$(git diff --name-only HEAD 2>/dev/null | grep -E '\.py$' | grep -v __pycache__ | wc -l | tr -d ' ')
  if [ "$changed_py" != "0" ]; then
    reminders="${reminders}${nl}- ${changed_py} Python file(s) changed. Consider running 'uv run pytest' or delegating to the test-author subagent before declaring done."
  fi
fi

# Migration unapplied?
if ls app/db/migrations/*.sql >/dev/null 2>&1; then
  newest_migration=$(ls -t app/db/migrations/*.sql 2>/dev/null | head -1)
  if [ -n "$newest_migration" ] && git rev-parse --git-dir >/dev/null 2>&1; then
    if git status --porcelain "$newest_migration" 2>/dev/null | grep -q .; then
      reminders="${reminders}${nl}- New migration file detected (${newest_migration}). If not yet applied, use mcp__supabase__apply_migration before stopping."
    fi
  fi
fi

if [ -n "$reminders" ]; then
  jq -n --arg r "$reminders" '{systemMessage:("# Before stopping" + $r)}'
else
  echo '{}'
fi
