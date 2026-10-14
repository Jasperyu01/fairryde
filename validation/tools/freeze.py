"""Freeze: SHA-256 of every KB file, plus counts. Run again at the end with --check to prove nothing changed.

    python3 validation/tools/freeze.py                                   # v0.1 layout: writes validation/00_freeze.json
    python3 validation/tools/freeze.py --out validation/round2/00_freeze.json
    python3 validation/tools/freeze.py --out validation/round2/00_freeze.json --check

The KB is the repository's kb/ directory (round 1 ran on a copy at /home/claude/work/kb; set FAIRRYDE_KB to use another
directory). The version comes from kb/rules.yaml meta.version. kb/private/ (pseudonym tables that never enter the repo),
caches and build backups are not hashed.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KB = Path(os.environ.get("FAIRRYDE_KB", ROOT / "kb"))
SKIP = {"__pycache__", "backup", "private"}


def digest():
    files = {}
    for p in sorted(KB.rglob("*")):
        if p.is_file() and not SKIP & set(p.relative_to(KB).parts):
            files[str(p.relative_to(KB))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return files


if __name__ == "__main__":
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else ROOT / "validation" / "00_freeze.json"
    out = out if out.is_absolute() else ROOT / out
    files = digest()
    if "--check" in sys.argv:
        frozen = json.loads(out.read_text())["files"]
        changed = [f for f in frozen if files.get(f) != frozen[f]]
        added = [f for f in files if f not in frozen]
        print(json.dumps({"unchanged": not changed and not added, "changed": changed, "added": added}, indent=1))
    else:
        import yaml
        sys.path.insert(0, str(KB / "tools"))
        from kbload import KB as K
        kb = K(KB)
        info = {"kb_version": str(yaml.safe_load((KB / "rules.yaml").read_text(encoding="utf-8"))["meta"]["version"]),
                "frozen_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
                "counts": {"rules": len(kb.rules), "vocabularies": len(kb.vocab), "case_leaves": len(kb.case_leaves),
                           "entities": len(kb.entities), "events": len(kb.y["ontology"]["events"]),
                           "relations": len(kb.y["ontology"]["relations"]), "roles": len(kb.y["ontology"]["roles"]),
                           "playbooks": len(kb.playbooks)},
                "files": files}
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(info, indent=1))
        print(json.dumps({k: v for k, v in info.items() if k != "files"}, indent=1), len(files), "files hashed")
