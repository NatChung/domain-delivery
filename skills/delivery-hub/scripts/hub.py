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


def package_tag(package_root: Path, version: str) -> str:
    """The tag pointing at HEAD, or the VERSION-derived tag when none is set."""
    result = subprocess.run(
        ["git", "-C", str(package_root), "tag", "--points-at", "HEAD"],
        capture_output=True,
        text=True,
    )
    tags = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    for tag in sorted(tags):
        if tag.lstrip("v") == version:
            return tag
    return f"v{version}"


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


def write_lock(hub_root: Path, package_root: Path, applied: list[str]) -> dict:
    version = package_version(package_root)
    lock = {
        "lock_version": LOCK_VERSION,
        "package": "domain-delivery",
        "path": SUBMODULE_DIR,
        "tag": package_tag(package_root, version),
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


def ensure_submodule(hub_root: Path, package_override: Path | None) -> Path:
    """Return the installed package root, initialising the submodule if needed."""
    if package_override is not None:
        return package_override.resolve()
    installed = hub_root / SUBMODULE_DIR
    if not installed.is_dir() or not any(installed.iterdir()):
        _git(hub_root, "submodule", "update", "--init", "--", SUBMODULE_DIR)
    if not (installed / "VERSION").is_file():
        raise HubError(
            f"{installed}: submodule is not checked out; "
            f"run `git submodule update --init -- {SUBMODULE_DIR}`"
        )
    return installed


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
    lock = write_lock(hub_root, package_root, [m.name for m in available_migrations(package_root)])
    print(f"installed {lock['package']} {lock['tag']} into {hub_root}")
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
    package_root = ensure_submodule(
        hub_root, Path(args.package) if args.package else None
    )

    version = package_version(package_root)
    if lock.get("version") != version:
        findings.append(
            f"lock version {lock.get('version')!r} != installed VERSION {version!r}"
        )
    if lock.get("tag") and lock["tag"].lstrip("v") != str(lock.get("version")):
        findings.append(f"lock tag {lock['tag']!r} does not match version {lock.get('version')!r}")

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
    print(f"healthy: {lock['package']} {lock['tag']} at {lock['commit'][:12]}")
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

    pending = pending_migrations(package_root, lock)
    applied = list(lock.get("migrations_applied") or [])
    for migration in pending:
        print(f"running migration {migration.name}")
        for note in run_migration(migration, hub_root):
            print(f"  {note}")
        applied.append(migration.name)

    previous = lock.get("tag")
    new_lock = write_lock(hub_root, package_root, applied)
    if new_lock["commit"] == lock.get("commit") and not pending:
        print(f"already at {new_lock['tag']} ({new_lock['commit'][:12]}); lock refreshed")
    else:
        print(f"upgraded {previous} -> {new_lock['tag']} ({new_lock['commit'][:12]})")
    print(f"  {len(pending)} migration(s) applied")
    print("  snapshots and evidence were not touched")
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

    p_init = sub.add_parser("init", help="install the workflow into a Hub")
    common(p_init)
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
    common(p_upgrade)
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
