#!/usr/bin/env python3
"""Validate the canonical template boundary manifest.

Pre-commit usage (pass_filenames mode):
    python check-templatefiles.py file1 file2 ...

CI / pipe usage:
    git diff --name-only origin/main...HEAD | python check-templatefiles.py

Full manifest integrity:
    python check-templatefiles.py --check-manifest
"""
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


CANONICAL_TEMPLATE_ORIGIN = re.compile(
    r"^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"(Aptica-Solutions/a-repo-template|szeltneraptica/repo-template)"
    r"(\.git)?/?$",
    re.IGNORECASE,
)


def find_repo_root() -> Path:
    current = Path(os.getcwd())
    for candidate in [current, *current.parents]:
        if (candidate / ".templatefiles").exists():
            return candidate
    return current


def is_canonical_template(root: Path) -> bool:
    """Require both the template marker and a canonical GitHub origin."""
    if not (root / ".is-template-repo").is_file():
        return False
    result = subprocess.run(
        ["git", "-C", str(root), "remote", "get-url", "origin"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(
        CANONICAL_TEMPLATE_ORIGIN.fullmatch(result.stdout.strip())
    )


def load_entries(root: Path) -> list[str]:
    manifest = root / ".templatefiles"
    if not manifest.exists():
        print("ERROR: .templatefiles not found in repo root.", file=sys.stderr)
        sys.exit(1)
    entries = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return entries


def load_distributable_entries(root: Path) -> set[str]:
    entries: set[str] = set()
    in_distributable = False
    for raw_line in (root / ".templatefiles").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("# DISTRIBUTABLE "):
            in_distributable = True
            continue
        if line.startswith("# TEMPLATE-INFRA "):
            break
        if in_distributable and line and not line.startswith("#"):
            entries.add(line)
    return entries


def validate_policy(root: Path) -> list[str]:
    policy_path = root / ".template-policy.json"
    if not policy_path.exists():
        return [".template-policy.json is required."]

    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f".template-policy.json is invalid: {error}"]

    errors = []
    allowed_policies = {"three-way", "seed"}
    if policy.get("schema_version") != 1:
        errors.append(".template-policy.json schema_version must be 1.")
    if policy.get("default_policy") not in allowed_policies:
        errors.append(
            ".template-policy.json default_policy must be three-way or seed."
        )

    profiles = policy.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        errors.append(".template-policy.json profiles must be a non-empty object.")
    else:
        for name, definition in profiles.items():
            includes = definition.get("include") if isinstance(definition, dict) else None
            if not isinstance(includes, list) or not all(
                isinstance(pattern, str) and pattern for pattern in includes
            ):
                errors.append(
                    f".template-policy.json profile '{name}' must have a string include list."
                )

    path_policies = policy.get("path_policies", {})
    if not isinstance(path_policies, dict):
        errors.append(".template-policy.json path_policies must be an object.")
    else:
        distributable = load_distributable_entries(root)
        unknown_paths = sorted(set(path_policies) - distributable)
        invalid_values = sorted(
            path
            for path, value in path_policies.items()
            if value not in allowed_policies
        )
        if unknown_paths:
            errors.append(
                "Policy paths missing from the DISTRIBUTABLE section:\n  "
                + "\n  ".join(unknown_paths)
            )
        if invalid_values:
            errors.append(
                "Paths with unsupported synchronization policies:\n  "
                + "\n  ".join(invalid_values)
            )
    return errors


def load_tracked(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {path for path in result.stdout.split("\0") if path}


def validate_manifest(root: Path, entries: list[str]) -> list[str]:
    errors = validate_policy(root)
    counts = Counter(entries)
    duplicates = sorted(path for path, count in counts.items() if count > 1)
    invalid = sorted(
        path
        for path in entries
        if Path(path).is_absolute()
        or Path(path).as_posix() != path
        or ".." in Path(path).parts
    )
    listed = set(entries)
    tracked = load_tracked(root)
    listed_but_untracked = sorted(listed - tracked)
    tracked_but_unlisted = sorted(tracked - listed)

    if duplicates:
        errors.append("Duplicate manifest entries:\n  " + "\n  ".join(duplicates))
    if invalid:
        errors.append(
            "Manifest paths must be relative, normalized POSIX paths:\n  "
            + "\n  ".join(invalid)
        )
    if listed_but_untracked:
        errors.append(
            "Listed paths that are not tracked by git:\n  "
            + "\n  ".join(listed_but_untracked)
        )
    if tracked_but_unlisted:
        errors.append(
            "Tracked paths missing from .templatefiles:\n  "
            + "\n  ".join(tracked_but_unlisted)
        )
    return errors


def main() -> None:
    root = find_repo_root()

    # GitHub template creation copies the marker, so marker-only detection would
    # incorrectly enforce the canonical boundary in an uninitialized project.
    if not is_canonical_template(root):
        sys.exit(0)

    args = sys.argv[1:]
    check_manifest = "--check-manifest" in args
    files = [arg for arg in args if arg != "--check-manifest"]
    entries = load_entries(root)

    if check_manifest:
        errors = validate_manifest(root, entries)
        if errors:
            print(
                "\nTemplate manifest integrity check failed:\n",
                file=sys.stderr,
            )
            for error in errors:
                print(f"{error}\n", file=sys.stderr)
            sys.exit(1)
        print("Template manifest integrity check passed.")

    if not files:
        if sys.stdin.isatty():
            sys.exit(0)
        files = [line.strip() for line in sys.stdin if line.strip()]

    if not files:
        sys.exit(0)

    allowed = set(entries)
    violations = [f for f in files if Path(f).as_posix() not in allowed]

    if violations:
        print(
            "\nTemplate boundary violation — these files are not in .templatefiles:\n",
            file=sys.stderr,
        )
        for f in violations:
            print(f"  {f}", file=sys.stderr)
        print(
            "\nIf this file belongs in the template, add it to .templatefiles.\n"
            "If it is project-specific, remove it from this commit.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
