"""P0 freeze: SHA-256 of every KB file, plus counts. Run again at the end with --check to prove nothing changed."""
import hashlib
import json
import sys
from pathlib import Path

KB = Path("/home/claude/work/kb")
OUT = Path(__file__).resolve().parent.parent / "00_freeze.json"


def digest():
    files = {}
    for p in sorted(KB.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and "backup" not in p.parts:
            files[str(p.relative_to(KB))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return files


if __name__ == "__main__":
    files = digest()
    if "--check" in sys.argv:
        frozen = json.loads(OUT.read_text())["files"]
        changed = [f for f in frozen if files.get(f) != frozen[f]]
        added = [f for f in files if f not in frozen]
        print(json.dumps({"unchanged": not changed and not added, "changed": changed, "added": added}, indent=1))
    else:
        sys.path.insert(0, str(KB / "tools"))
        from kbload import KB as K
        kb = K(KB)
        info = {"kb_version": "0.1.0", "frozen_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
                "counts": {"rules": len(kb.rules), "vocabularies": len(kb.vocab), "case_leaves": len(kb.case_leaves),
                           "entities": len(kb.entities), "events": len(kb.y["ontology"]["events"]),
                           "relations": len(kb.y["ontology"]["relations"]), "roles": len(kb.y["ontology"]["roles"]),
                           "playbooks": len(kb.playbooks)},
                "files": files}
        OUT.write_text(json.dumps(info, indent=1))
        print(json.dumps({k: v for k, v in info.items() if k != "files"}, indent=1), len(files), "files hashed")
