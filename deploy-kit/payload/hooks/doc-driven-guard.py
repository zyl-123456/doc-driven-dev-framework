#!/usr/bin/env python3
"""Optional WorkBuddy adapter v3: short session entry, no per-message nagging."""
import json
import sys
from pathlib import Path

DOC_NAME = "00-驱动开发规则.md"
DOC_DIRS = ("开发驱动文档", ".", "docs/开发驱动文档", "文档/开发驱动文档")


def find_root(cwd):
    current = Path(cwd).resolve()
    for parent in [current] + list(current.parents)[:5]:
        if any((parent / directory / DOC_NAME).is_file() for directory in DOC_DIRS):
            return parent
    return None


def response(data):
    if data.get("hook_event_name") != "SessionStart":
        return {"continue": True}
    if not data.get("cwd"):
        return {"continue": True}
    root = find_root(data["cwd"])
    if root is None:
        return {"continue": True}
    entry = root / "START_HERE.md"
    context = "[文档驱动项目] 先看 %s，按本任务读取相关需求、约束和证据。" % entry.as_posix()
    if entry.is_file():
        for line in entry.read_text(encoding="utf-8").splitlines():
            if any(line.strip().startswith("- **" + key + "**") for key in ("正在做", "卡在哪", "下一步")):
                context += "\n" + line[:100]
    context += "\n快照仅供定位，对照当前输入；普通讨论无需开发收尾。"
    return {"continue": True, "hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": context[:600]}}


def main():
    try:
        data = json.loads(sys.stdin.read())
        out = response(data) if isinstance(data, dict) else {"continue": True}
    except Exception:
        # Adapters must never block human input, including malformed payloads.
        out = {"continue": True}
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
