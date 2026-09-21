#!/usr/bin/env python3
"""Safely synchronize versioned template assets into a downstream repository."""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, Sequence


SOURCE_REPOSITORY = "Aptica-Solutions/a-repo-template"
TEMPLATE_MARKER = ".is-template-repo"
SUPPORTED_POLICIES = {"three-way", "seed", "sectioned", "overwrite"}
REPO_BLOCK_BEGIN = b"<!-- repo-rules:begin -->"
REPO_BLOCK_END = b"<!-- repo-rules:end -->"
# git merge-file reports conflict counts up to this value; anything higher
# is a genuine tool error rather than a conflicted merge.
MERGE_CONFLICT_LIMIT = 127
SUPPORTED_PROFILES = {
    "standard",
    "standard-local-docs",
    "nested-template",
    "lightweight",
    "exempt",
}
CANONICAL_TEMPLATE_ORIGIN = re.compile(
    r"^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"(Aptica-Solutions/a-repo-template|szeltneraptica/repo-template)"
    r"(\.git)?/?$",
    re.IGNORECASE,
)


class SyncError(RuntimeError):
    """Raised for an operational or configuration failure."""


class SyncConflict(SyncError):
    """Raised after reporting one or more synchronization conflicts."""


@dataclass(frozen=True)
class GitResult:
    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class PendingWrite:
    content: bytes


def run_git(
    root: Path,
    *arguments: str,
    check: bool = True,
) -> GitResult:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
    )
    result = GitResult(
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )
    if check and result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise SyncError(f"git {' '.join(arguments)} failed: {detail}")
    return result


def git_text(root: Path, *arguments: str, check: bool = True) -> str:
    return run_git(root, *arguments, check=check).stdout.decode(
        "utf-8", errors="strict"
    )


def validate_relative_path(raw_path: str, label: str) -> str:
    if not raw_path or "\\" in raw_path:
        raise SyncError(f"{label} must be a normalized relative POSIX path: {raw_path!r}")
    path = PurePosixPath(raw_path)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != raw_path:
        raise SyncError(f"{label} must be a normalized relative POSIX path: {raw_path!r}")
    return raw_path


def repository_path(root: Path, relative_path: str, label: str = "Path") -> Path:
    normalized = validate_relative_path(relative_path, label)
    destination = root.joinpath(*PurePosixPath(normalized).parts)
    try:
        destination.resolve(strict=False).relative_to(root.resolve())
    except ValueError as error:
        raise SyncError(f"{label} escapes the repository root: {relative_path!r}") from error
    return destination


def resolve_repository_root() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise SyncError("Not inside a git repository.")
    return Path(completed.stdout.strip()).resolve()


def remote_url(root: Path, remote: str) -> str | None:
    result = run_git(root, "remote", "get-url", remote, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", errors="strict").strip()


def is_canonical_template(root: Path) -> bool:
    if not repository_path(root, TEMPLATE_MARKER).is_file():
        return False
    origin = remote_url(root, "origin")
    return bool(origin and CANONICAL_TEMPLATE_ORIGIN.fullmatch(origin))


def resolve_template_ref(root: Path, remote: str, requested_ref: str) -> str:
    remotes = git_text(root, "remote").splitlines()
    if remote not in remotes:
        raise SyncError(
            f"Remote '{remote}' not found. Add it with: "
            f"git remote add {remote} https://github.com/{SOURCE_REPOSITORY}.git"
        )

    candidates = (
        [f"{remote}/{requested_ref}", requested_ref]
        if "/" not in requested_ref
        else [requested_ref]
    )
    for candidate in candidates:
        result = run_git(
            root,
            "rev-parse",
            "--verify",
            f"{candidate}^{{commit}}",
            check=False,
        )
        if result.returncode == 0:
            return candidate
    raise SyncError(
        f"Template ref '{requested_ref}' was not found. "
        f"Run 'git fetch --tags {remote}' first."
    )


def ref_bytes(root: Path, ref: str, relative_path: str) -> bytes:
    validate_relative_path(relative_path, "Template path")
    return run_git(root, "show", f"{ref}:{relative_path}").stdout


def ref_blob(root: Path, ref: str, relative_path: str) -> str | None:
    validate_relative_path(relative_path, "Template path")
    result = run_git(
        root,
        "rev-parse",
        f"{ref}:{relative_path}",
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode("ascii").strip()


def worktree_blob(root: Path, relative_path: str) -> str | None:
    destination = repository_path(root, relative_path, "Managed path")
    if not destination.is_file():
        return None
    result = run_git(
        root,
        "hash-object",
        f"--path={relative_path}",
        "--",
        relative_path,
    )
    return result.stdout.decode("ascii").strip()


def ref_history_contains_blob(
    root: Path,
    ref: str,
    relative_path: str,
    blob: str,
) -> bool:
    """Return whether a worktree blob is an exact historical template version."""
    validate_relative_path(relative_path, "Template path")
    objects = run_git(
        root,
        "rev-list",
        ref,
        "--objects",
        "--",
        relative_path,
    ).stdout.splitlines()
    expected = blob.encode("ascii")
    return any(line.split(b" ", 1)[0] == expected for line in objects)


def load_policy(root: Path, ref: str) -> dict[str, Any]:
    try:
        policy = json.loads(ref_bytes(root, ref, ".template-policy.json"))
    except json.JSONDecodeError as error:
        raise SyncError(f".template-policy.json is invalid: {error}") from error

    if policy.get("schema_version") != 1:
        raise SyncError(
            "Unsupported .template-policy.json schema version "
            f"{policy.get('schema_version')!r}."
        )
    if policy.get("default_policy") not in SUPPORTED_POLICIES:
        raise SyncError("Template default_policy must be 'three-way' or 'seed'.")
    if not isinstance(policy.get("profiles"), dict):
        raise SyncError("Template profiles must be an object.")
    if not isinstance(policy.get("path_policies", {}), dict):
        raise SyncError("Template path_policies must be an object.")
    retired = policy.get("retired_paths", {})
    if not isinstance(retired, dict):
        raise SyncError("Template retired_paths must be an object.")
    for retired_path, disposition in retired.items():
        validate_relative_path(retired_path, "Retired path")
        target = disposition.get("absorb_into") if isinstance(disposition, dict) else None
        if not isinstance(target, str):
            raise SyncError(
                f"Retired path '{retired_path}' must define a string absorb_into."
            )
        validate_relative_path(target, "Retired absorb_into path")
    return policy


def profile_patterns(
    policy: dict[str, Any],
    profile: str,
    key: str,
    required: bool,
) -> list[str]:
    profile_definition = policy["profiles"].get(profile)
    if not isinstance(profile_definition, dict):
        raise SyncError(f"Profile '{profile}' is not defined in .template-policy.json.")
    patterns = profile_definition.get(key)
    if patterns is None and not required:
        return []
    if not isinstance(patterns, list) or not all(
        isinstance(pattern, str) and pattern for pattern in patterns
    ):
        raise SyncError(f"Profile '{profile}' must define a string {key} list.")
    for pattern in patterns:
        validate_relative_path(pattern, f"Profile {key} pattern")
    return patterns


def excluded_by_profile(relative_path: str, exclude_patterns: Sequence[str]) -> bool:
    """Return whether a profile disclaims ownership of a template path.

    An excluded path is neither delivered nor deleted: the downstream repository
    owns it outright, so a lingering lock entry must not be read as a template
    removal.
    """
    return any(
        fnmatch.fnmatchcase(relative_path, pattern) for pattern in exclude_patterns
    )


def distributable_paths(root: Path, ref: str) -> list[str]:
    """Return every path the template distributes, before any profile narrows it."""
    content = ref_bytes(root, ref, ".templatefiles").decode("utf-8")
    files: list[str] = []
    in_distributable = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("# DISTRIBUTABLE "):
            in_distributable = True
            continue
        if line.startswith("# TEMPLATE-INFRA "):
            break
        if not in_distributable or not line or line.startswith("#"):
            continue
        validate_relative_path(line, "Manifest entry")
        if PurePosixPath(line).name.startswith(".TODO"):
            continue
        files.append(line)
    return files


def manifest_files(root: Path, ref: str, policy: dict[str, Any], profile: str) -> list[str]:
    include_patterns = profile_patterns(policy, profile, "include", True)
    exclude_patterns = profile_patterns(policy, profile, "exclude", False)
    return [
        line
        for line in distributable_paths(root, ref)
        if not excluded_by_profile(line, exclude_patterns)
        and any(fnmatch.fnmatchcase(line, pattern) for pattern in include_patterns)
    ]


def split_repo_block(content: bytes) -> tuple[bytes, bytes, bytes] | None:
    """Return (before, block, after) around the repo-owned block, markers excluded."""
    begin = content.find(REPO_BLOCK_BEGIN)
    end = content.find(REPO_BLOCK_END)
    if begin < 0 or end < begin:
        return None
    start = begin + len(REPO_BLOCK_BEGIN)
    return content[:start], content[start:end], content[end:]


def sectioned_content(source: bytes, current: bytes | None, current_is_template: bool) -> bytes:
    """Template text with the downstream repo-owned block carried over.

    The template owns everything outside the markers. The downstream repository
    owns what sits between them, so this policy never conflicts. A file with no
    markers migrates once: content that was never a template version moves into
    the block whole, and an untouched template version keeps the default block.
    """
    parts = split_repo_block(source)
    if parts is None or current is None:
        return source
    before, _, after = parts
    downstream = split_repo_block(current)
    if downstream is not None:
        block = downstream[1]
    elif current_is_template:
        return source
    else:
        block = b"\n" + current.strip() + b"\n"
    return before + block + after


def downstream_additions(current: bytes, baseline: bytes) -> bytes:
    """Lines the downstream repository added to a template file, in order.

    What a repository contributed to a template-owned file is exactly what it
    added relative to the version it received. Deletions and untouched template
    text carry nothing worth keeping once the template retires the file.
    """
    current_lines = current.decode("utf-8", errors="replace").splitlines()
    baseline_lines = baseline.decode("utf-8", errors="replace").splitlines()
    added: list[str] = []
    matcher = difflib.SequenceMatcher(a=baseline_lines, b=current_lines, autojunk=False)
    for tag, _, _, start, end in matcher.get_opcodes():
        if tag in {"insert", "replace"}:
            if added and added[-1] != "":
                added.append("")
            added.extend(current_lines[start:end])
    while added and not added[-1].strip():
        added.pop()
    while added and not added[0].strip():
        added.pop(0)
    if not any(line.strip() for line in added):
        return b""
    return ("\n".join(added) + "\n").encode("utf-8")


def absorb_into_block(target: bytes, retired_path: str, additions: bytes) -> bytes | None:
    """Append a retired file's downstream additions to the repo-owned block.

    Returns None when the target has no repo-owned block. Re-running is a no-op:
    the carried-over heading marks content that has already been absorbed.
    """
    parts = split_repo_block(target)
    if parts is None:
        return None
    before, block, after = parts
    heading = f"## Carried over from `{retired_path}`".encode("utf-8")
    if heading in block:
        return target
    note = (
        b"The template retired that file. These are the lines this repository had "
        b"added to it. Review and tidy.\n\n"
    )
    return before + block.rstrip(b"\n") + b"\n\n" + heading + b"\n\n" + note + additions + after


def load_lock(root: Path, lock_path: str) -> dict[str, Any] | None:
    destination = repository_path(root, lock_path, "Lock path")
    if not destination.is_file():
        return None
    try:
        lock = json.loads(destination.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SyncError(f"{lock_path} is invalid: {error}") from error
    if lock.get("schema_version") != 1:
        raise SyncError(f"Unsupported lock schema version {lock.get('schema_version')!r}.")
    if lock.get("source_repository") != SOURCE_REPOSITORY:
        raise SyncError(
            f"Lock source {lock.get('source_repository')!r} is not {SOURCE_REPOSITORY}."
        )
    if not isinstance(lock.get("files"), dict):
        raise SyncError("Lock files must be an object.")
    return lock


def merge_bytes(current: bytes, baseline: bytes, requested: bytes) -> bytes | None:
    with tempfile.TemporaryDirectory(prefix="aptica-template-merge-") as temp_name:
        temp_root = Path(temp_name)
        current_path = temp_root / "current"
        baseline_path = temp_root / "baseline"
        requested_path = temp_root / "requested"
        current_path.write_bytes(current)
        baseline_path.write_bytes(baseline)
        requested_path.write_bytes(requested)
        completed = subprocess.run(
            [
                "git",
                "merge-file",
                "-p",
                "-L",
                "downstream",
                "-L",
                "previous-template",
                "-L",
                "requested-template",
                str(current_path),
                str(baseline_path),
                str(requested_path),
            ],
            check=False,
            capture_output=True,
        )
        # git merge-file returns the number of conflicts, capped at 127, not a
        # plain 0/1. Treating any count above one as a tool failure aborted the
        # whole run on files that simply conflicted in more than one hunk.
        if completed.returncode == 0:
            return completed.stdout
        if 0 < completed.returncode <= MERGE_CONFLICT_LIMIT:
            return None
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SyncError(
            f"git merge-file failed with exit {completed.returncode}: "
            f"{detail or 'no diagnostic output'}"
        )


def add_result(
    results: list[dict[str, str]],
    path: str,
    action: str,
    policy: str,
    detail: str = "",
) -> None:
    results.append(
        {
            "path": path,
            "action": action,
            "policy": policy,
            "detail": detail,
        }
    )


def write_atomic(destination: Path, content: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        delete=False,
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_json(destination: Path, document: dict[str, Any]) -> None:
    payload = (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    write_atomic(destination, payload)


def print_results(results: list[dict[str, str]]) -> None:
    if not results:
        print("No files are owned by the selected profile.")
        return
    widths = {
        key: max(len(key), *(len(item[key]) for item in results))
        for key in ("path", "action", "policy")
    }
    print(
        f"{'path':<{widths['path']}}  "
        f"{'action':<{widths['action']}}  "
        f"{'policy':<{widths['policy']}}  detail"
    )
    print(
        f"{'-' * widths['path']}  "
        f"{'-' * widths['action']}  "
        f"{'-' * widths['policy']}  {'-' * 6}"
    )
    for item in results:
        print(
            f"{item['path']:<{widths['path']}}  "
            f"{item['action']:<{widths['action']}}  "
            f"{item['policy']:<{widths['policy']}}  "
            f"{item['detail']}"
        )


def synchronize(arguments: argparse.Namespace) -> dict[str, Any]:
    root = resolve_repository_root()
    if is_canonical_template(root):
        raise SyncError(
            "Refusing to run downstream synchronization in the canonical "
            f"{SOURCE_REPOSITORY} checkout."
        )
    stale_template_marker = repository_path(root, TEMPLATE_MARKER).is_file()
    resolved_ref = resolve_template_ref(
        root,
        arguments.template_remote,
        arguments.template_ref,
    )
    source_commit = git_text(
        root,
        "rev-parse",
        f"{resolved_ref}^{{commit}}",
    ).strip()
    release = arguments.template_release or arguments.template_ref
    policy = load_policy(root, resolved_ref)
    files = manifest_files(root, resolved_ref, policy, arguments.profile)
    still_distributed = set(distributable_paths(root, resolved_ref))
    exclude_patterns = profile_patterns(policy, arguments.profile, "exclude", False)
    lock = load_lock(root, arguments.lock_path)

    old_commit = str(lock["template_commit"]) if lock else ""
    if old_commit:
        old_probe = run_git(
            root,
            "cat-file",
            "-e",
            f"{old_commit}^{{commit}}",
            check=False,
        )
        if old_probe.returncode != 0:
            raise SyncError(
                f"The previous template commit '{old_commit}' is unavailable. "
                "Fetch template history before syncing."
            )

    results: list[dict[str, str]] = []
    new_file_state: OrderedDict[str, dict[str, str]] = OrderedDict()
    pending_writes: OrderedDict[str, PendingWrite] = OrderedDict()
    pending_deletes: list[str] = []
    retired_modified: list[str] = []

    if stale_template_marker:
        add_result(
            results,
            TEMPLATE_MARKER,
            "delete",
            "downstream-marker",
            "Copied template-source marker is invalid in a downstream repository.",
        )
        pending_deletes.append(TEMPLATE_MARKER)

    for relative_path in files:
        source_blob = ref_blob(root, resolved_ref, relative_path)
        if source_blob is None:
            add_result(
                results,
                relative_path,
                "conflict",
                "unknown",
                "Listed in manifest but absent from template ref.",
            )
            continue

        path_policy = policy["path_policies"].get(
            relative_path,
            policy["default_policy"],
        )
        if path_policy not in SUPPORTED_POLICIES:
            add_result(
                results,
                relative_path,
                "conflict",
                str(path_policy),
                "Unsupported path policy.",
            )
            continue

        current_blob = worktree_blob(root, relative_path)
        locked_file = lock["files"].get(relative_path) if lock else None
        baseline_blob = (
            str(locked_file.get("template_blob"))
            if isinstance(locked_file, dict) and locked_file.get("template_blob")
            else None
        )
        new_file_state[relative_path] = {
            "template_blob": source_blob,
            "policy": path_policy,
        }

        if current_blob == source_blob:
            add_result(results, relative_path, "unchanged", path_policy)
            continue

        if path_policy in {"sectioned", "overwrite"} and current_blob is not None:
            source_content = ref_bytes(root, resolved_ref, relative_path)
            current_content = repository_path(root, relative_path).read_bytes()
            if path_policy == "overwrite":
                requested, detail = source_content, "Template owns this file outright."
            else:
                is_template = current_blob == baseline_blob or ref_history_contains_blob(
                    root, resolved_ref, relative_path, current_blob
                )
                requested = sectioned_content(source_content, current_content, is_template)
                detail = (
                    "Repo-owned block kept."
                    if split_repo_block(current_content) is not None or is_template
                    else "Migrated: previous downstream content moved into the repo-owned block."
                )
            if requested == current_content:
                add_result(results, relative_path, "unchanged", path_policy)
            else:
                add_result(results, relative_path, "update", path_policy, detail)
                pending_writes[relative_path] = PendingWrite(requested)
            continue

        if path_policy == "seed" and current_blob is not None:
            add_result(
                results,
                relative_path,
                "preserve",
                path_policy,
                "Seed file already exists.",
            )
            continue

        source_content = ref_bytes(root, resolved_ref, relative_path)
        if current_blob is None:
            add_result(results, relative_path, "add", path_policy)
            pending_writes[relative_path] = PendingWrite(source_content)
            continue

        if baseline_blob is None:
            if not arguments.accept_existing_as_baseline and ref_history_contains_blob(
                root,
                resolved_ref,
                relative_path,
                current_blob,
            ):
                # No lock entry, but the file is byte-for-byte a version the
                # template once shipped, so nothing downstream can be lost.
                add_result(
                    results,
                    relative_path,
                    "update",
                    path_policy,
                    "No baseline, but the file is an exact historical template version.",
                )
                pending_writes[relative_path] = PendingWrite(source_content)
                continue
            if arguments.accept_existing_as_baseline:
                if ref_history_contains_blob(
                    root,
                    resolved_ref,
                    relative_path,
                    current_blob,
                ):
                    add_result(
                        results,
                        relative_path,
                        "update",
                        path_policy,
                        "Existing file is an exact historical template version.",
                    )
                    pending_writes[relative_path] = PendingWrite(source_content)
                else:
                    add_result(
                        results,
                        relative_path,
                        "preserve",
                        path_policy,
                        "Existing file accepted as a downstream customization.",
                    )
            else:
                add_result(
                    results,
                    relative_path,
                    "conflict",
                    path_policy,
                    "No baseline; rerun with --accept-existing-as-baseline after review.",
                )
            continue

        if current_blob == baseline_blob:
            add_result(results, relative_path, "update", path_policy)
            pending_writes[relative_path] = PendingWrite(source_content)
            continue

        if source_blob == baseline_blob:
            add_result(
                results,
                relative_path,
                "preserve",
                path_policy,
                "Downstream-only change.",
            )
            continue

        current_content = repository_path(root, relative_path).read_bytes()
        baseline_content = ref_bytes(root, old_commit, relative_path)
        merged_content = merge_bytes(
            current_content,
            baseline_content,
            source_content,
        )
        if merged_content is None:
            add_result(
                results,
                relative_path,
                "conflict",
                path_policy,
                "Both template and downstream changed; manual merge required.",
            )
        else:
            add_result(results, relative_path, "merge", path_policy)
            pending_writes[relative_path] = PendingWrite(merged_content)

    if lock:
        for relative_path, locked_file in lock["files"].items():
            validate_relative_path(relative_path, "Locked path")
            if relative_path in new_file_state:
                continue
            if excluded_by_profile(relative_path, exclude_patterns):
                add_result(
                    results,
                    relative_path,
                    "preserve",
                    "excluded",
                    "Profile excludes this path; downstream owns it.",
                )
                continue
            if relative_path in still_distributed:
                # The template still ships this path; this profile just does not
                # own it. That is a profile change, not a template removal, so
                # the file is released to the repository: never deleted, never
                # a conflict, and dropped from the lock.
                add_result(
                    results,
                    relative_path,
                    "preserve",
                    "released",
                    "Outside this profile; downstream owns it.",
                )
                continue
            baseline_blob = str(locked_file.get("template_blob", ""))
            current_blob = worktree_blob(root, relative_path)
            if current_blob is None:
                add_result(
                    results,
                    relative_path,
                    "unchanged",
                    "removed",
                    "Already absent.",
                )
            elif current_blob == baseline_blob:
                add_result(results, relative_path, "delete", "removed")
                pending_deletes.append(relative_path)
            elif relative_path in policy.get("retired_paths", {}):
                retired_modified.append(relative_path)
            else:
                add_result(
                    results,
                    relative_path,
                    "conflict",
                    "removed",
                    "Removed from template but modified downstream.",
                )

    for relative_path in retired_modified:
        target_path = policy["retired_paths"][relative_path]["absorb_into"]
        additions = downstream_additions(
            repository_path(root, relative_path).read_bytes(),
            ref_bytes(root, old_commit, relative_path),
        )
        if not additions:
            add_result(
                results,
                relative_path,
                "delete",
                "retired",
                "Retired by the template; downstream only removed text, nothing to keep.",
            )
            pending_deletes.append(relative_path)
            continue
        if target_path in pending_writes:
            target_content: bytes | None = pending_writes[target_path].content
        elif target_path in new_file_state and repository_path(root, target_path).is_file():
            target_content = repository_path(root, target_path).read_bytes()
        else:
            target_content = None
        absorbed = (
            absorb_into_block(target_content, relative_path, additions)
            if target_content is not None
            else None
        )
        if absorbed is None:
            add_result(
                results,
                relative_path,
                "conflict",
                "retired",
                f"Retired and modified downstream, but {target_path} has no repo-owned "
                "block in this profile to absorb it.",
            )
            continue
        pending_writes[target_path] = PendingWrite(absorbed)
        for item in results:
            if item["path"] == target_path and item["action"] == "unchanged":
                item["action"] = "update"
        for item in results:
            if item["path"] == target_path:
                item["detail"] = (
                    item["detail"] + " " if item["detail"] else ""
                ) + f"Absorbed downstream additions from {relative_path}."
        add_result(
            results,
            relative_path,
            "delete",
            "retired",
            f"Retired by the template; downstream additions moved into {target_path}.",
        )
        pending_deletes.append(relative_path)

    conflicts = [item for item in results if item["action"] == "conflict"]
    changes = [
        item
        for item in results
        if item["action"] in {"add", "update", "merge", "delete"}
    ]
    report: dict[str, Any] = {
        "schema_version": 1,
        "mode": "apply" if arguments.apply else "dry-run",
        "source_commit": source_commit,
        "template_release": release,
        "template_profile": arguments.profile,
        "conflicts": len(conflicts),
        "changes": len(changes),
        "results": results,
    }
    if arguments.report_path:
        write_json(
            repository_path(root, arguments.report_path, "Report path"),
            report,
        )

    print_results(results)
    print(
        f"\nMode: {report['mode']}; "
        f"changes: {len(changes)}; conflicts: {len(conflicts)}"
    )
    if conflicts:
        raise SyncConflict(
            f"Template sync stopped with {len(conflicts)} conflict(s). "
            "No managed files or lock state were written."
        )
    if not arguments.apply:
        print("Dry run only. Review the table, then rerun with --apply.")
        return report

    for relative_path, pending in pending_writes.items():
        write_atomic(repository_path(root, relative_path), pending.content)
    for relative_path in pending_deletes:
        repository_path(root, relative_path).unlink()

    lock_document: dict[str, Any] = {
        "schema_version": 1,
        "source_repository": SOURCE_REPOSITORY,
        "template_release": release,
        "template_commit": source_commit,
        "template_profile": arguments.profile,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "files": new_file_state,
    }
    write_json(
        repository_path(root, arguments.lock_path, "Lock path"),
        lock_document,
    )
    print(f"Lock updated: {arguments.lock_path}")
    print("Review the diff, then commit the synchronized files and lock together.")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template-remote", default="template")
    parser.add_argument("--template-ref", default="main")
    parser.add_argument(
        "--profile",
        choices=sorted(SUPPORTED_PROFILES),
        default="standard",
    )
    parser.add_argument("--template-release", default="")
    parser.add_argument("--lock-path", default=".aptica/template-lock.json")
    parser.add_argument("--report-path", default="")
    parser.add_argument("--accept-existing-as-baseline", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser


def fail(message: str, returncode: int) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(returncode)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        synchronize(arguments)
    except SyncConflict as error:
        fail(str(error), 2)
    except (OSError, UnicodeError, SyncError) as error:
        fail(str(error), 1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
