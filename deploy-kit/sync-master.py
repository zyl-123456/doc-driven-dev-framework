#!/usr/bin/env python3
"""Generate repository-owned release copies; never import installed skills."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ["00-驱动开发规则.md", "01-人类需求描述.md", "02-需求技术拆解.md",
        "03-技术实现方案.md", "04-实现过程记录.md", "START_HERE.md", "verify.py"]
MASTER = CORE + ["README.md", "文档导读.md", "框架评价与边界.md", "交接与迭代优化清单.md",
                 "VERSION", "AGENTS.md", "CHANGELOG.md", "CONTRIBUTING.md", ".gitattributes", ".gitignore"]
SKILLS = ("doc-driven-dev", "doc-driven-framework-porting")


def emit(text):
    """CLI uses UTF-8; imported helpers also tolerate a legacy host stream."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(text.encode(encoding, errors="backslashreplace").decode(encoding))


def source_map(root):
    sources = {"master/" + name: root / name for name in MASTER}
    for directory in ("releases", "tests", "skills", ".github"):
        for path in sorted((root / directory).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                sources["master/" + path.relative_to(root).as_posix()] = path
    for name in SKILLS:
        sources["skills/" + name + "/SKILL.md"] = root / "skills" / name / "SKILL.md"
    for name in CORE:
        sources["skills/doc-driven-framework-porting/templates/" + name] = root / name
    sources["hooks/doc-driven-guard.py"] = root / "hooks" / "doc-driven-guard.py"
    return sources


def sync(root=ROOT, check=False):
    root = Path(root).resolve()
    payload = root / "deploy-kit" / "payload"
    sources = source_map(root)
    missing = [name for name, path in sources.items() if not path.is_file()]
    if missing:
        emit("FAIL 缺少源文件: " + ", ".join(missing))
        return 1
    current = {p.relative_to(payload).as_posix() for directory in ("master", "skills", "hooks")
               for p in (payload / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    extras = current - sources.keys()
    changes = [name for name, path in sources.items()
               if not (payload / name).is_file() or (payload / name).read_bytes() != path.read_bytes()]
    manifest = {"version": (root / "VERSION").read_text(encoding="utf-8").strip(),
                "files": {name: hashlib.sha256(path.read_bytes()).hexdigest()
                          for name, path in sorted(sources.items())}}
    expected = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    manifest_path = payload / "manifest.json"
    manifest_changed = not manifest_path.is_file() or manifest_path.read_text(encoding="utf-8") != expected
    if extras:
        emit("FAIL 未识别副本（不自动删除）: " + ", ".join(sorted(extras)))
        return 1
    if not check:
        for name in changes:
            target = payload / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(sources[name].read_bytes())
        if manifest_changed:
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_bytes(expected.encode("utf-8"))
    different = bool(changes or manifest_changed)
    emit("%s 副本 %d 份，差异 %d，清单%s；未读写用户级技能或配置" % (
        "FAIL" if check and different else "PASS", len(sources), len(changes),
        "有差异" if manifest_changed else "一致"))
    if check and changes:
        emit("\n".join(changes))
    return 1 if check and different else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return sync(args.master, args.check)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
