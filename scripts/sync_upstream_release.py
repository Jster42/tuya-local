#!/usr/bin/env python3
"""Merge the latest make-all/tuya-local release into this fork and push it."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_URL = "https://github.com/make-all/tuya-local.git"
PROFILES = {
    "custom_components/tuya_local/devices/meowant_sc10_litterbox.yaml": "wyvu1hlo3s9weqt9",
    "custom_components/tuya_local/devices/security_light_white.yaml": "hhlk7fgmxl5n7fhx",
}
DEVICE_LINES = (
    "Meowant SC10 litter box",
    "PIR floodlight (Security Light white)",
)


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, check=check)


def capture(args: list[str]) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def require_identity() -> None:
    missing = [
        name
        for name in (
            "GIT_AUTHOR_NAME",
            "GIT_AUTHOR_EMAIL",
            "GIT_COMMITTER_NAME",
            "GIT_COMMITTER_EMAIL",
        )
        if not os.environ.get(name)
    ]
    if missing:
        raise SystemExit("Missing git identity: " + ", ".join(missing))


def ensure_upstream() -> None:
    remotes = capture(["git", "remote"]).split()
    if "upstream" not in remotes:
        run(["git", "remote", "add", "upstream", UPSTREAM_URL])


def latest_release_tag() -> str:
    request = urllib.request.Request(
        "https://api.github.com/repos/make-all/tuya-local/releases/latest",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "tuya-local-fork-sync",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    tag = payload.get("tag_name")
    if not tag:
        raise SystemExit("Upstream latest release has no tag")
    return tag


def custom_profiles_kept(before: str) -> None:
    changed = subprocess.run(
        ["git", "diff", "--quiet", before, "HEAD", "--", *PROFILES],
        cwd=ROOT,
        check=False,
    ).returncode
    if changed:
        raise SystemExit("A custom device profile changed in the merge. Not pushing.")
    devices = (ROOT / "DEVICES.md").read_text()
    for entry in DEVICE_LINES:
        if entry not in devices:
            raise SystemExit(f"DEVICES.md lost {entry}")
    for path, product in PROFILES.items():
        if product not in (ROOT / path).read_text():
            raise SystemExit(f"{path} lost product {product}")


def abandon_merge(before: str) -> None:
    if (ROOT / ".git" / "MERGE_HEAD").exists():
        run(["git", "merge", "--abort"])
        return
    run(["git", "reset", "--hard", before])


def main() -> None:
    require_identity()
    os.chdir(ROOT)
    run(["git", "checkout", "main"])
    run(["git", "pull", "--ff-only", "origin", "main"])
    ensure_upstream()
    tag = latest_release_tag()
    print(f"Latest upstream release: {tag}")
    run(["git", "fetch", "upstream", f"refs/tags/{tag}:refs/remotes/upstream/release"])
    if (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", "refs/remotes/upstream/release", "HEAD"],
            cwd=ROOT,
            check=False,
        ).returncode
        == 0
    ):
        print(f"main already contains {tag}")
        return

    before = capture(["git", "rev-parse", "HEAD"])
    merged = subprocess.run(
        [
            "git",
            "merge",
            "--no-edit",
            "-m",
            f"Merge upstream release {tag}",
            "refs/remotes/upstream/release",
        ],
        cwd=ROOT,
        check=False,
    )
    if merged.returncode != 0:
        sys.path.insert(0, str(ROOT / ".github" / "scripts"))
        from resolve_sync_conflicts import main as resolve_conflicts

        try:
            resolve_conflicts()
        except SystemExit:
            abandon_merge(before)
            raise
        run(["git", "add", "DEVICES.md"])
        run(["git", "commit", "--no-edit"])

    try:
        custom_profiles_kept(before)
    except SystemExit:
        abandon_merge(before)
        raise

    run(["git", "push", "origin", "HEAD:main"])
    print(f"Pushed merge of {tag}")


if __name__ == "__main__":
    main()
