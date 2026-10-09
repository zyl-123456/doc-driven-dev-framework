#!/usr/bin/env python3
"""Install optional WorkBuddy adapters; preserve unrelated configuration and memory."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUARD = "doc-driven-guard.py"


def payload_valid(payload):
    try:
        manifest = json.loads((payload / "manifest.json").read_text(encoding="utf-8"))
        files = manifest["files"]
        if not isinstance(files, dict) or not files:
            raise ValueError("清单为空")
        for name, expected in files.items():
            path = (payload / name).resolve()
            if payload.resolve() not in path.parents:
                raise ValueError("清单路径超出 payload")
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("发布副本校验失败: " + name)
        return True, manifest["version"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return False, str(exc)


def write_bytes(path, data, dry=False):
    if path.is_file() and path.read_bytes() == data:
        return False
    if dry:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(path.name + ".bak-" + uuid.uuid4().hex[:12])
        shutil.copy2(path, backup)
    path.write_bytes(data)
    return True


def copy_tree(source, target, dry=False):
    return sum(write_bytes(target / p.relative_to(source), p.read_bytes(), dry)
               for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def update_hooks(data, command):
    """Replace only this adapter, including stale v4 paths and per-message hooks."""
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("hooks 不是对象")
    for event in ("SessionStart", "UserPromptSubmit"):
        entries = hooks.get(event, [])
        if not isinstance(entries, list):
            raise ValueError(event + " 不是列表")
        kept = []
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("hooks"), list):
                kept.append(entry)
                continue
            remaining = [h for h in entry["hooks"] if not (
                isinstance(h, dict) and GUARD in str(h.get("command", "")))]
            if remaining:
                kept.append(dict(entry, hooks=remaining))
        if event == "SessionStart":
            kept.append({"matcher": "startup", "hooks": [
                {"type": "command", "command": command, "timeout": 10}]})
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--master-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--with-codebuddy", action="store_true")
    args = parser.parse_args()
    payload = HERE / "payload"
    valid, detail = payload_valid(payload)
    if not valid:
        print("FAIL " + detail)
        return 1
    home = args.home.expanduser().resolve()
    wb = home / ".workbuddy"
    master = (args.master_dir or wb / "templates" / "doc-driven-master").resolve()
    guard_src = payload / "hooks" / GUARD
    # Validate script behavior before touching user configuration.
    for event, cwd, should_inject in [("SessionStart", payload / "master", True),
                                      ("UserPromptSubmit", payload / "master", False)]:
        result = subprocess.run([sys.executable, str(guard_src)],
                                input=json.dumps({"cwd": str(cwd), "hook_event_name": event}),
                                text=True, encoding="utf-8", capture_output=True, timeout=15)
        try:
            response = json.loads(result.stdout)
            injected = bool(response.get("hookSpecificOutput", {}).get("additionalContext"))
            if result.returncode or response.get("continue") is not True or injected != should_inject:
                raise ValueError("钩子行为不符合 v5 约定")
        except (ValueError, AttributeError):
            print("FAIL 钩子自测: " + event)
            return 1
    command = '"%s" "%s"' % (Path(sys.executable).as_posix(), (wb / "hooks" / GUARD).as_posix())
    configs = [wb / "settings.json"]
    secondary = home / ".codebuddy" / "settings.json"
    if args.with_codebuddy or secondary.is_file():
        configs.append(secondary)
    prepared = []
    try:
        for path in configs:
            old = path.read_text(encoding="utf-8") if path.is_file() else "{}"
            data = json.loads(old)
            if not isinstance(data, dict):
                raise ValueError("配置顶层不是对象")
            if path == secondary and not args.with_codebuddy and GUARD not in old:
                continue
            updated = update_hooks(data, command)
            prepared.append((path, (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode("utf-8")))
    except (OSError, ValueError, TypeError) as exc:
        print("FAIL 配置不可合并，未改用户配置: " + str(exc))
        return 1
    changed = copy_tree(payload / "skills", wb / "skills", args.dry_run)
    changed += write_bytes(wb / "hooks" / GUARD, guard_src.read_bytes(), args.dry_run)
    changed += copy_tree(payload / "master", master, args.dry_run)
    for path, data in prepared:
        changed += write_bytes(path, data, args.dry_run)
    if not args.dry_run:
        result = subprocess.run([sys.executable, str(master / "verify.py"), "--mode", "template"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if result.returncode:
            print(result.stdout)
            print("FAIL 母版结构检查")
            return 1
    print("PASS v%s，%s %d 份变更；未改写用户记忆" % (detail, "计划" if args.dry_run else "完成", changed))
    print("客户端触发仍需重启并验证；脚本自测不代表平台已生效。")
    legacy = wb / "MEMORY.md"
    if legacy.is_file() and "开发项目治理（常设命令" in legacy.read_text(encoding="utf-8"):
        print("WARN 存在 v4 全局治理记忆；请按授权单独核对旧规则，本安装器不会修改。")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
