#!/usr/bin/env python3
"""Finish an upstream merge when DEVICES.md is the only conflict."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

CONFLICT = re.compile(
    r"<<<<<<<[^\n]*\n(.*?)=======\n(.*?)>>>>>>>[^\n]*\n",
    re.DOTALL,
)


def conflicted_files() -> list[str]:
    output = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        text=True,
    )
    return [line for line in output.splitlines() if line]


def unique_lines(block: str) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for line in block.splitlines(keepends=True):
        key = line.strip()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line if line.endswith("\n") else line + "\n")
    return lines


def merge_hunk(match: re.Match[str]) -> str:
    ours = unique_lines(match.group(1))
    seen = {line.strip() for line in ours}
    theirs = [line for line in unique_lines(match.group(2)) if line.strip() not in seen]
    return "".join(ours + theirs)


def main() -> None:
    conflicted = conflicted_files()
    unexpected = [name for name in conflicted if name != "DEVICES.md"]
    if unexpected:
        raise SystemExit(
            "Not merging automatically. Conflicts are outside the device list: "
            + ", ".join(unexpected)
        )
    if conflicted != ["DEVICES.md"]:
        raise SystemExit("Merge stopped without a device-list conflict to resolve")

    path = Path("DEVICES.md")
    resolved = CONFLICT.sub(merge_hunk, path.read_text())
    if "<<<<<<<" in resolved or ">>>>>>>" in resolved:
        raise SystemExit("DEVICES.md still contains conflict markers")
    path.write_text(resolved)


if __name__ == "__main__":
    main()
