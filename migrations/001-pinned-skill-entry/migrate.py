"""Add a pinned Skill entry without replacing local workflow policies."""
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
MARKER = "<!-- domain-delivery:skill-entry -->"
END_MARKER = "<!-- /domain-delivery:skill-entry -->"


def migrate(hub_root):
    hub_root = Path(hub_root)
    source = (PACKAGE_ROOT / "template/docs/skill-entry.md").read_bytes()
    entry = hub_root / "docs/skill-entry.md"
    if (hub_root / "docs").is_symlink() or entry.is_symlink():
        raise ValueError("existing Skill entry path is a symlink; reconcile it before upgrade")
    if entry.exists() and entry.read_bytes() != source:
        raise ValueError("existing docs/skill-entry.md differs; reconcile it before upgrade")
    template = (PACKAGE_ROOT / "template/CLAUDE.md").read_text()
    pointer = MARKER + template.split(MARKER, 1)[1].split(END_MARKER, 1)[0] + END_MARKER + "\n"
    writes = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = hub_root / name
        if path.is_symlink():
            raise ValueError(f"existing {name} is a symlink; reconcile it before upgrade")
        content = path.read_text() if path.exists() else ""
        if MARKER in content:
            if pointer.strip() not in content:
                raise ValueError(f"existing {name} entry differs; reconcile it before upgrade")
            continue
        writes.append((path, content.rstrip() + "\n\n" + pointer))
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_bytes(source)
    for path, content in writes:
        path.write_text(content)
    return ["installed pinned Skill entry; existing workflow scope preserved"]
