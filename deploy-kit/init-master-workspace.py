#!/usr/bin/env python3
"""Create a usable master workspace from a verified deployment kit."""
import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("kit_install", HERE / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=HERE.parent)
    parser.add_argument("--init-git", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    target = args.target.expanduser().resolve()
    if target == HERE or HERE in target.parents:
        print("FAIL 目标不能位于 deploy-kit 内部")
        return 1
    valid, version = installer.payload_valid(HERE / "payload")
    if not valid:
        print("FAIL " + version)
        return 1
    changed = installer.copy_tree(HERE / "payload" / "master", target, args.dry_run)
    changed += installer.copy_tree(HERE / "payload" / "hooks", target / "hooks", args.dry_run)
    destination_kit = target / "deploy-kit"
    if destination_kit.resolve() != HERE:
        changed += installer.copy_tree(HERE, destination_kit, args.dry_run)
    if args.dry_run:
        print("PASS 计划 %d 份变更（未写盘）" % changed)
        return 0
    if args.init_git:
        probe = subprocess.run(["git", "-C", str(target), "rev-parse", "--show-toplevel"],
                               capture_output=True, text=True)
        if probe.returncode:
            for command in (["init", "-b", "main"], ["add", "-A"],
                            ["commit", "-m", "chore: initialize document-driven framework v" + version]):
                result = subprocess.run(["git", "-C", str(target)] + command,
                                        capture_output=True, text=True, encoding="utf-8", errors="replace")
                if result.returncode:
                    print("FAIL Git 初始化或提交；检查 Git 身份，文件已保留")
                    return 1
    check = subprocess.run([sys.executable, str(target / "verify.py"), "--mode", "template"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check.returncode:
        print(check.stdout)
        return 1
    print("PASS v%s 母版已建立，%d 份变更；目录 %s" % (version, changed, target))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
