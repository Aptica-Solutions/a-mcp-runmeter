#!/usr/bin/env python3
"""Strip AI-assistant Co-Authored-By trailers from commit messages.

Aptica policy: AI coding assistants must not attribute themselves as git
co-authors. This runs as a pre-commit `commit-msg` hook, so it applies no
matter which assistant produced the commit (Claude, Codex, Copilot,
Cursor, and so on). Implemented in Python rather than sed/grep so it
behaves identically on macOS, Linux, and Windows dev machines.

pre-commit passes the path to the commit message file as the first arg.
"""
from __future__ import annotations

import re
import sys

# Matches a Co-Authored-By trailer attributed to a known AI assistant.
# Case-insensitive, so it catches both "Co-authored-by:" and "Co-Authored-By:".
_AI_COAUTHOR = re.compile(
    r"^\s*Co-authored-by:\s*"
    r"(claude|codex|github copilot|copilot|cursor|gemini|aider|devin)\b",
    re.IGNORECASE,
)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 0
    msg_path = argv[1]
    with open(msg_path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()
    kept = [line for line in lines if not _AI_COAUTHOR.match(line)]
    if kept != lines:
        with open(msg_path, "w", encoding="utf-8") as handle:
            handle.writelines(kept)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
