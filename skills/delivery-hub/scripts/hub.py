#!/usr/bin/env python3
"""Delivery Hub lifecycle commands: init, doctor and upgrade.

The shared workflow package is installed in a Hub as a Git submodule at the
fixed path `.domain-delivery/` and pinned by `workflow.lock` (ADR 0008). These
commands create that installation, report on it, and move it forward.

Exit codes: ``0`` pass, ``1`` findings, ``2`` invalid input or refused action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PASS, FAIL, INVALID = 0, 1, 2

PACKAGE_ROOT = Path(__file__).resolve().parents[3]
SUBMODULE_DIR = ".domain-delivery"
LOCK_NAME = "workflow.lock"
LOCK_VERSION = 1


# Hub content the template must never overwrite, even with --force: this is
# meaning and execution basis the Hub owns, not template output.
PROTECTED_PREFIXES = ("docs/domain/", "specs/", "evidence/")

PLACEHOLDER = "{{PROJECT}}"


class HubError(Exception):
    """A refusal or an invalid request, reported without a traceback."""


# --------------------------------------------------------------------------
# package identity


def released_files(package_root: Path) -> list[str]:
    """Every file the release ships, as sorted repository-relative paths.

    The list is whatever Git tracks. Naming directories here instead would mean
    a new top-level folder silently falls outside the digest, and `docs/` —
    which carries the method every Hub pins — did exactly that.
    """
    listing = _git_raw(package_root, "ls-files", "-z").split("\0")
    return sorted(entry for entry in listing if entry)


def untracked_files(package_root: Path) -> list[str]:
    """Files present in the installation that the release does not ship."""
    listing = _git_raw(
        package_root, "ls-files", "-z", "--others", "--exclude-standard"
    ).split("\0")
    return sorted(entry for entry in listing if entry)


def package_digest(package_root: Path) -> str:
    """Hash the released bytes: sorted relative paths, then each file's content.

    Paths are hashed too, so a rename changes the digest, and the list is sorted
    so the result never depends on filesystem order.
    """
    digest = hashlib.sha256()
    for relative in released_files(package_root):
        path = package_root / relative
        if not path.is_file():
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def package_version(package_root: Path) -> str:
    version_file = package_root / "VERSION"
    if not version_file.is_file():
        raise HubError(f"{package_root}: no VERSION file")
    version = version_file.read_text(encoding="utf-8").strip()
    if not version:
        raise HubError(f"{version_file}: VERSION is empty")
    return version


def _git_raw(repo: Path, *args: str) -> str:
    """Run git and return stdout untouched.

    Porcelain status encodes state in the first two columns, so the leading
    space of an unstaged entry is data, not padding. Callers that parse
    column-aligned output must use this, not the stripped variant.
    """
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise HubError(f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}")
    return result.stdout


def _git(repo: Path, *args: str) -> str:
    return _git_raw(repo, *args).strip()


def package_commit(package_root: Path) -> str:
    return _git(package_root, "rev-parse", "HEAD")


def package_tag(package_root: Path, version: str) -> str | None:
    """The release tag pointing at HEAD, or None.

    A tag is never synthesised from VERSION. An untagged commit is not a
    release, and recording `v{VERSION}` for one would let any working state be
    reported as a published version.
    """
    result = subprocess.run(
        ["git", "-C", str(package_root), "tag", "--points-at", "HEAD"],
        capture_output=True,
        text=True,
    )
    tags = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    for tag in sorted(tags):
        if tag.lstrip("v") == version:
            return tag
    return None


def dirty_paths(repo: Path, ignore: str | None = None) -> list[str]:
    """Uncommitted paths, optionally excluding one.

    Moving the submodule is how an upgrade starts, so the submodule's own entry
    must not be what blocks it. Everything else still does.
    """
    paths = []
    for line in _git_raw(repo, "status", "--porcelain").splitlines():
        entry = line[3:].strip()
        if " -> " in entry:                 # a rename reports "old -> new"
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip('"').rstrip("/")
        if not entry:
            continue
        if ignore is not None and (entry == ignore or entry.startswith(ignore + "/")):
            continue
        paths.append(entry)
    return paths


# --------------------------------------------------------------------------
# lock file


def recorded_gitlink(hub_root: Path) -> str | None:
    """The submodule commit the Hub's own history records, if any.

    This is what a fresh clone checks out. It can differ from what is checked
    out here, and from what the lock says — an upgrade is exactly that window —
    so the three have to be compared, not assumed equal.
    """
    result = subprocess.run(
        ["git", "-C", str(hub_root), "rev-parse", f"HEAD:{SUBMODULE_DIR}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    commit = result.stdout.strip()
    return commit if re.fullmatch(r"[0-9a-f]{40}", commit) else None


def version_key(version: str) -> tuple:
    """Sortable SemVer form.

    A prerelease precedes the release it leads to, so `1.0.0-alpha` sorts below
    `1.0.0`. Numeric identifiers compare numerically and below alphanumeric
    ones, as the specification requires. Anything unparseable sorts as text.
    """
    release, _, prerelease = version.partition("-")
    core = tuple(
        (0, int(chunk)) if chunk.isdigit() else (1, chunk)
        for chunk in release.split(".")
    )
    if not prerelease:
        # 1 sorts above the 0 used by every prerelease below.
        return (core, 1, ())
    identifiers = tuple(
        (0, int(chunk), "") if chunk.isdigit() else (1, 0, chunk)
        for chunk in prerelease.split(".")
    )
    return (core, 0, identifiers)


def read_lock(hub_root: Path) -> dict:
    path = hub_root / LOCK_NAME
    if not path.is_file():
        raise HubError(f"{path}: no {LOCK_NAME}; run init first")
    try:
        lock = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HubError(f"{path}: not valid JSON: {exc}") from exc
    if not isinstance(lock, dict):
        raise HubError(f"{path}: {LOCK_NAME} must be a JSON object")
    return lock


def require_release_tag(
    package_root: Path, version: str, allow_untagged: bool
) -> str | None:
    """The release tag for this checkout, refusing an untagged one.

    Release identity is a precondition, not a closing formality. `upgrade` asks
    this before it runs anything, so an untagged package is refused while the
    Hub is still untouched rather than after migrations have already changed it.
    """
    tag = package_tag(package_root, version)
    if tag is None and not allow_untagged:
        raise HubError(
            f"{package_root}: no Git tag `v{version}` points at the checked-out "
            f"commit, so this is not a release and the lock will not claim it is. "
            f"Check out a tagged release, or pass --allow-untagged to record an "
            f"untagged installation that `doctor` will keep reporting."
        )
    return tag


def write_lock(
    hub_root: Path,
    package_root: Path,
    applied: list[str],
    allow_untagged: bool = False,
) -> dict:
    version = package_version(package_root)
    tag = require_release_tag(package_root, version, allow_untagged)
    lock = {
        "lock_version": LOCK_VERSION,
        "package": "domain-delivery",
        "path": SUBMODULE_DIR,
        "tag": tag,
        "version": version,
        "commit": package_commit(package_root),
        "package_digest": package_digest(package_root),
        "migrations_applied": applied,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (hub_root / LOCK_NAME).write_text(
        json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return lock


# --------------------------------------------------------------------------
# migrations


def available_migrations(package_root: Path) -> list[Path]:
    base = package_root / "migrations"
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir() and (p / "migrate.py").is_file())


def pending_migrations(package_root: Path, lock: dict) -> list[Path]:
    applied = set(lock.get("migrations_applied") or [])
    return [m for m in available_migrations(package_root) if m.name not in applied]


IMMUTABLE_PREFIXES = ("specs/", "evidence/")


def immutable_fingerprint(hub_root: Path) -> dict[str, str]:
    """Digest every file under the immutable prefixes, keyed by relative path.

    A migration runs as ordinary Python inside this process, so it cannot be
    sandboxed. What can be guaranteed is that a migration which touched the
    delivered record does not survive: the change is detected, undone from Git,
    and the upgrade fails.
    """
    fingerprint = {}
    for prefix in IMMUTABLE_PREFIXES:
        base = hub_root / prefix.rstrip("/")
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file():
                relative = path.relative_to(hub_root).as_posix()
                fingerprint[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return fingerprint


def immutable_change(hub_root: Path, before: dict[str, str]) -> list[str]:
    """Paths under the immutable prefixes that differ from the fingerprint."""
    after = immutable_fingerprint(hub_root)
    return sorted(
        relative
        for relative in set(before) | set(after)
        if after.get(relative) != before.get(relative)
    )


def _restore_note(unrestored: list[str]) -> str:
    """Say what the restore actually achieved, never what it attempted."""
    if not unrestored:
        return "The delivered record has been restored from Git."
    return (
        f"The delivered record could NOT be fully restored; fix these by hand "
        f"before trusting the Hub: {', '.join(unrestored[:5])}."
    )


def restore_immutable(hub_root: Path, before: dict[str, str]) -> list[str]:
    """Undo whatever a migration did to the immutable trees.

    The fingerprint taken before the migration is the restore instruction, not
    just the detector. A path the migration added is not in Git, so `checkout`
    would leave it behind: it is deleted. A path the migration changed or
    removed is tracked, so it is checked out by name — including a whole tree
    the migration deleted, which an `exists()` guard would have skipped.

    Returns the paths that are still wrong afterwards. An empty list is the only
    thing that entitles the caller to say the record was restored.
    """
    after = immutable_fingerprint(hub_root)

    for relative in sorted(set(after) - set(before)):
        path = hub_root / relative
        try:
            path.unlink()
        except OSError:
            continue

    tracked = sorted(
        relative
        for relative in before
        if after.get(relative) != before[relative]
    )
    if tracked:
        subprocess.run(
            ["git", "-C", str(hub_root), "checkout", "--", *tracked],
            capture_output=True,
            text=True,
        )

    restored = immutable_fingerprint(hub_root)
    return sorted(
        relative
        for relative in set(before) | set(restored)
        if restored.get(relative) != before.get(relative)
    )


def run_migration(migration: Path, hub_root: Path) -> list[str]:
    namespace: dict = {"__file__": str(migration / "migrate.py")}
    exec(compile((migration / "migrate.py").read_text(encoding="utf-8"),
                 str(migration / "migrate.py"), "exec"), namespace)
    migrate = namespace.get("migrate")
    if not callable(migrate):
        raise HubError(f"{migration}: migrate.py defines no migrate(hub_root)")
    notes = migrate(hub_root)
    return list(notes or [])


# --------------------------------------------------------------------------
# template rendering


def template_files(package_root: Path) -> list[Path]:
    base = package_root / "template"
    if not base.is_dir():
        raise HubError(f"{base}: no template directory in the package")
    return sorted(p for p in base.rglob("*") if p.is_file())


def is_protected(relative: str) -> bool:
    return any(relative.startswith(prefix) for prefix in PROTECTED_PREFIXES)


def render(text: str, project: str) -> str:
    return text.replace(PLACEHOLDER, project)


def install_template(
    package_root: Path, hub_root: Path, project: str, force: bool
) -> tuple[list[str], list[str]]:
    """Copy template files into the Hub. Never deletes; never overwrites unless
    ``force``, and never overwrites protected Hub content even then."""
    base = package_root / "template"
    added: list[str] = []
    replaced: list[str] = []
    for source in template_files(package_root):
        relative = source.relative_to(base).as_posix()
        target = hub_root / relative
        if target.exists():
            if not force or is_protected(relative):
                continue
            replaced.append(relative)
        else:
            added.append(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            render(source.read_text(encoding="utf-8"), project), encoding="utf-8"
        )
    return added, replaced


# --------------------------------------------------------------------------
# submodule


INIT_HINT = f"run `git submodule update --init -- {SUBMODULE_DIR}`"


def resolve_package(hub_root: Path, package_override: Path | None) -> Path:
    """Return the installed package root without touching anything.

    Raises when the submodule is absent, so a read-only caller can report it
    rather than fetch on the user's behalf.
    """
    if package_override is not None:
        return package_override.resolve()
    installed = hub_root / SUBMODULE_DIR
    if not (installed / "VERSION").is_file():
        raise HubError(f"{installed}: the workflow is not checked out; {INIT_HINT}")
    return installed


def ensure_submodule(hub_root: Path, package_override: Path | None) -> Path:
    """Return the installed package root, initialising the submodule if needed.

    Only the commands that already change the Hub may call this: it can clone
    over the network and write to the working tree. `doctor` must not.
    """
    if package_override is not None:
        return package_override.resolve()
    installed = hub_root / SUBMODULE_DIR
    if not installed.is_dir() or not any(installed.iterdir()):
        _git(hub_root, "submodule", "update", "--init", "--", SUBMODULE_DIR)
    return resolve_package(hub_root, None)


# --------------------------------------------------------------------------
# commands


def cmd_init(args) -> int:
    hub_root = Path(args.hub).resolve()
    if not hub_root.is_dir():
        raise HubError(f"{hub_root}: no such directory")
    if (hub_root / LOCK_NAME).is_file():
        raise HubError(
            f"{hub_root / LOCK_NAME} already exists; this Hub is installed. "
            f"Use `upgrade` to move it to a new version."
        )
    package_root = ensure_submodule(
        hub_root, Path(args.package) if args.package else None
    )
    added, replaced = install_template(package_root, hub_root, args.project, args.force)
    lock = write_lock(
        hub_root,
        package_root,
        [m.name for m in available_migrations(package_root)],
        allow_untagged=args.allow_untagged,
    )
    print(f"installed {lock['package']} {lock['tag'] or 'untagged'} into {hub_root}")
    for relative in added:
        print(f"  added    {relative}")
    for relative in replaced:
        print(f"  replaced {relative}")
    if not added and not replaced:
        print("  no template files were missing")
    print(f"  lock     {LOCK_NAME} ({lock['package_digest']})")
    return PASS


def cmd_doctor(args) -> int:
    hub_root = Path(args.hub).resolve()
    findings: list[str] = []
    lock = read_lock(hub_root)
    try:
        package_root = resolve_package(
            hub_root, Path(args.package) if args.package else None
        )
    except HubError as exc:
        print("1 finding(s):")
        print(f"  - {exc}")
        return FAIL

    version = package_version(package_root)
    if lock.get("version") != version:
        findings.append(
            f"lock version {lock.get('version')!r} != installed VERSION {version!r}"
        )
    if lock.get("tag") and lock["tag"].lstrip("v") != str(lock.get("version")):
        findings.append(f"lock tag {lock['tag']!r} does not match version {lock.get('version')!r}")

    # The lock's tag text agreeing with VERSION says nothing about Git. Ask Git
    # which tag points at the installed HEAD, so a deleted or moved release tag
    # is a finding instead of a healthy report.
    if lock.get("tag"):
        checked_out_tag = package_tag(package_root, version)
        if checked_out_tag != lock["tag"]:
            findings.append(
                f"lock tag {lock['tag']!r} does not point at the checked-out "
                f"commit; Git reports {checked_out_tag or 'no matching tag'} there"
            )

    commit = package_commit(package_root)
    if lock.get("commit") != commit:
        findings.append(
            f"lock commit {str(lock.get('commit'))[:12]} != checked-out {commit[:12]}"
        )

    digest = package_digest(package_root)
    if lock.get("package_digest") != digest:
        findings.append("package digest does not match the lock; the installation was modified")

    for stray in untracked_files(package_root):
        findings.append(f"untracked file inside the installation: {stray}")

    for modified in dirty_paths(package_root):
        findings.append(f"modified file inside the installation: {modified}")

    if lock.get("tag") is None:
        findings.append(
            f"lock records no release tag; the installed commit is not a tagged "
            f"release, so this Hub is pinned to an unpublished state"
        )

    if args.package is None:
        gitlink = recorded_gitlink(hub_root)
        if gitlink is None:
            findings.append(
                f"this Hub's history records no {SUBMODULE_DIR} gitlink, so a fresh "
                f"clone would install no workflow at all. Commit the submodule."
            )
        elif gitlink != lock.get("commit"):
            findings.append(
                f"lock commit {str(lock.get('commit'))[:12]} != committed gitlink "
                f"{gitlink[:12]}; a fresh clone would install a different version. "
                f"Commit the submodule move and the lock together."
            )

    for relative in ("hub.yaml", "CONTEXT-MAP.md", "docs/domain/INDEX.md",
                     ".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"):
        if not (hub_root / relative).is_file():
            findings.append(f"missing Hub file: {relative}")

    hub_yaml = hub_root / "hub.yaml"
    if hub_yaml.is_file() and PLACEHOLDER in hub_yaml.read_text(encoding="utf-8"):
        findings.append(f"hub.yaml still contains the {PLACEHOLDER} placeholder")

    pending = pending_migrations(package_root, lock)
    for migration in pending:
        findings.append(f"pending migration: {migration.name}")

    if findings:
        print(f"{len(findings)} finding(s):")
        for finding in findings:
            print(f"  - {finding}")
        return FAIL
    print(f"healthy: {lock['package']} {lock['tag'] or 'untagged'} at {lock['commit'][:12]}")
    return PASS


def cmd_upgrade(args) -> int:
    hub_root = Path(args.hub).resolve()
    lock = read_lock(hub_root)
    dirty = dirty_paths(hub_root, ignore=SUBMODULE_DIR)
    if dirty:
        listed = ", ".join(sorted(dirty)[:5])
        more = "" if len(dirty) <= 5 else f" (+{len(dirty) - 5} more)"
        raise HubError(
            f"{hub_root}: working tree is dirty; commit or set aside changes "
            f"before upgrading: {listed}{more}"
        )
    package_root = ensure_submodule(
        hub_root, Path(args.package) if args.package else None
    )

    installation_dirty = dirty_paths(package_root) + untracked_files(package_root)
    if installation_dirty:
        listed = ", ".join(sorted(installation_dirty)[:5])
        more = "" if len(installation_dirty) <= 5 else f" (+{len(installation_dirty) - 5} more)"
        raise HubError(
            f"{package_root}: the installed workflow has uncommitted changes, so "
            f"the lock would bless hand-edited bytes. Restore it with "
            f"`git -C {SUBMODULE_DIR} checkout .` or send the change upstream: "
            f"{listed}{more}"
        )

    pending = pending_migrations(package_root, lock)
    # Release identity is checked before the first migration runs, not when the
    # lock is written. An untagged package that failed only at write_lock had
    # already mutated the Hub by then, which ADR 0008's pinning rule forbids.
    require_release_tag(
        package_root, package_version(package_root), args.allow_untagged
    )

    applied = list(lock.get("migrations_applied") or [])
    for migration in pending:
        print(f"running migration {migration.name}")
        before = immutable_fingerprint(hub_root)
        try:
            notes = run_migration(migration, hub_root)
        except BaseException as exc:
            # A migration that raises has still already written whatever it
            # wrote, so the immutable trees are restored on this path too.
            unrestored = restore_immutable(hub_root, before)
            raise HubError(
                f"{migration.name}: the migration failed with "
                f"{type(exc).__name__}: {exc}. {_restore_note(unrestored)} "
                f"The upgrade stopped and the lock was not updated."
            ) from exc

        touched = immutable_change(hub_root, before)
        if touched:
            unrestored = restore_immutable(hub_root, before)
            raise HubError(
                f"{migration.name}: a migration changed the immutable delivered "
                f"record, which no upgrade may rewrite: "
                f"{', '.join(touched[:5])}. {_restore_note(unrestored)} "
                f"The upgrade stopped and the lock was not updated."
            )
        for note in notes:
            print(f"  {note}")
        applied.append(migration.name)

    previous = lock.get("tag")
    previous_version = str(lock.get("version") or "")
    new_lock = write_lock(
        hub_root, package_root, applied, allow_untagged=args.allow_untagged
    )
    if new_lock["commit"] == lock.get("commit") and not pending:
        print(
            f"already at {new_lock['tag'] or 'untagged'} "
            f"({new_lock['commit'][:12]}); lock refreshed"
        )
    else:
        if previous_version and version_key(new_lock["version"]) < version_key(previous_version):
            direction = "downgraded"
        elif previous_version and version_key(new_lock["version"]) == version_key(previous_version):
            direction = "moved"
        else:
            direction = "upgraded"
        print(
            f"{direction} {previous or 'untagged'} -> "
            f"{new_lock['tag'] or 'untagged'} ({new_lock['commit'][:12]})"
        )
    print(f"  {len(pending)} migration(s) applied")
    print("  snapshots and evidence were not touched")
    if args.package is None:
        gitlink = recorded_gitlink(hub_root)
        if gitlink is not None and gitlink != new_lock["commit"]:
            print("  next: commit the submodule move and workflow.lock together")
    return PASS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--hub", default=".", help="Hub root (default: current directory)")
        p.add_argument(
            "--package",
            default=None,
            help=f"package root; defaults to <hub>/{SUBMODULE_DIR}",
        )

    def writes_lock(p):
        common(p)
        p.add_argument(
            "--allow-untagged",
            action="store_true",
            help="record an installation whose commit carries no release tag; "
                 "doctor keeps reporting it",
        )

    p_init = sub.add_parser("init", help="install the workflow into a Hub")
    writes_lock(p_init)
    p_init.add_argument("--project", required=True, help="Hub project name")
    p_init.add_argument(
        "--force",
        action="store_true",
        help="overwrite template-generated files; never docs/domain/**, specs/** or evidence/**",
    )
    p_init.set_defaults(func=cmd_init)

    p_doctor = sub.add_parser("doctor", help="report on the installation (read-only)")
    common(p_doctor)
    p_doctor.set_defaults(func=cmd_doctor)

    p_upgrade = sub.add_parser("upgrade", help="move the Hub to the checked-out version")
    writes_lock(p_upgrade)
    p_upgrade.set_defaults(func=cmd_upgrade)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except HubError as exc:
        print(str(exc), file=sys.stderr)
        return INVALID


if __name__ == "__main__":
    raise SystemExit(main())
