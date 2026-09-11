#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init-master-workspace.py —— 把解压出来的部署包，整理成一个「母版工作区」

为什么需要这一步：
    解压 deploy-kit 之后，母版文档还躺在 payload/master/ 里面（三层深），
    那不是你能直接用的「顶层设计」目录。
    本脚本把母版铺到指定目录的**根**，配好 hooks/ 与 .gitignore，
    让这个目录跟老设备的母版工作区（`D:\\000-me-work\\top_design`）**完全同构**：
    于是 verify.py / sync-master.py / package.py 都能在这儿正常跑，
    新项目也能直接以它为「原生态母版」取源。

整理后的结构：
    <目标目录>/                     ← 这就是「顶层设计 / 母版工作区」
    ├── 00~04 五文档
    ├── README.md  START_HERE.md  verify.py
    ├── 文档导读.md  框架评价与边界.md  交接与迭代优化清单.md
    ├── hooks/doc-driven-guard.py   ← 触发层钩子（权威源）
    ├── .gitignore
    └── deploy-kit/…                ← 部署包原样保留（用于再分发 / 打包）

用法：
    python init-master-workspace.py                  # 目标 = deploy-kit 的上一级
    python init-master-workspace.py --target "D:/top_design"
    python init-master-workspace.py --init-git       # 顺便建 git 库 + 首次提交
    python init-master-workspace.py --dry-run        # 只看会做什么，不写盘

安全设计：幂等（内容相同则跳过）、覆盖前备份（.bak-<日期>）、拒绝把母版铺进 deploy-kit 内部。
"""

import argparse
import datetime
import filecmp
import os
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PAYLOAD = os.path.join(HERE, "payload")
PAYLOAD_MASTER = os.path.join(PAYLOAD, "master")
PAYLOAD_HOOKS = os.path.join(PAYLOAD, "hooks")
GUARD = "doc-driven-guard.py"
DATE = datetime.datetime.now().strftime("%Y%m%d")

GITIGNORE = """# ---------------------------------------------------------------
# 打包产物：dist/ 里的 zip 可用 deploy-kit 重新打包生成。
# 二进制文件每次重打包都会产生差异、污染历史，所以不进版本库。
# 需要传输包时：python deploy-kit/sync-master.py && python deploy-kit/package.py
/dist/

# Python 缓存
__pycache__/
*.py[cod]

# 自检/临时目录（install.py 的 --home 测试用）
_selftest/

# 备份文件（install.py / 技能安装产生的 .bak-<日期>）
*.bak
*.bak-*

# 编辑器 / 系统
.vscode/
.idea/
*.swp
.DS_Store
Thumbs.db
"""

results = []


def rec(ok, title, detail=""):
    results.append((ok, title, detail))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", title, (" —— " + detail) if detail else ""))


def backup(path):
    if not os.path.exists(path):
        return None
    dst = "%s.bak-%s" % (path, DATE)
    if os.path.isdir(path):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(path, dst)
    else:
        shutil.copy2(path, dst)
    return dst


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", timeout=60)


def repo_root(path):
    """path 是否已在某个 git 工作区内；是则返回仓库根，否则 None。"""
    try:
        r = run(["git", "-C", path, "rev-parse", "--show-toplevel"])
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=os.path.dirname(HERE),
                    help="母版工作区目录，默认 deploy-kit 的上一级")
    ap.add_argument("--init-git", action="store_true",
                    help="顺便建 git 版本库并做首次提交（母版工作区推荐）")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写盘")
    args = ap.parse_args()

    target = os.path.abspath(args.target)
    dry = args.dry_run

    print("=" * 62)
    print("把部署包整理成「母版工作区」  %s" % ("（DRY-RUN 只报告）" if dry else ""))
    print("=" * 62)
    print("来源: %s" % PAYLOAD_MASTER)
    print("目标: %s" % target)

    # ---------- 前置检查 ----------
    if not os.path.isdir(PAYLOAD_MASTER):
        rec(False, "部署包完整", "找不到 %s" % PAYLOAD_MASTER)
        return finish()
    names = [n for n in sorted(os.listdir(PAYLOAD_MASTER))
             if os.path.isfile(os.path.join(PAYLOAD_MASTER, n))]
    rec(len(names) >= 7, "部署包完整", "payload/master 有 %d 份" % len(names))

    here_abs = os.path.abspath(HERE)
    if target == here_abs or target.startswith(here_abs + os.sep):
        rec(False, "目标目录合法", "目标是 deploy-kit 内部，会把包结构搞乱；请指到它的上一级或别处")
        return finish()

    if not dry:
        os.makedirs(target, exist_ok=True)

    # ---------- 1. 母版 → 工作区根 ----------
    copied, backed = 0, 0
    for n in names:
        src = os.path.join(PAYLOAD_MASTER, n)
        dst = os.path.join(target, n)
        if os.path.isfile(dst) and filecmp.cmp(src, dst, shallow=False):
            continue
        if dry:
            copied += 1
            continue
        if os.path.exists(dst):
            if backup(dst):
                backed += 1
        shutil.copy2(src, dst)
        copied += 1
    rec(True, "母版（五文档 + 入口 + 验收 + 理解材料）→ 工作区根",
        "复制 %d 份%s" % (copied, ("，覆盖前已备份 %d 份" % backed) if backed else "") if copied
        else "已是最新（%d 份）" % len(names))

    # ---------- 2. hooks/ ----------
    guard_src = os.path.join(PAYLOAD_HOOKS, GUARD)
    guard_dst = os.path.join(target, "hooks", GUARD)
    if not os.path.isfile(guard_src):
        rec(False, "触发层钩子 → hooks/", "payload/hooks 里没有 %s" % GUARD)
    elif dry:
        rec(True, "触发层钩子 → hooks/", "将写入 %s" % guard_dst)
    else:
        os.makedirs(os.path.dirname(guard_dst), exist_ok=True)
        if os.path.isfile(guard_dst) and filecmp.cmp(guard_src, guard_dst, shallow=False):
            rec(True, "触发层钩子 → hooks/", "已是最新")
        else:
            if os.path.exists(guard_dst):
                backup(guard_dst)
            shutil.copy2(guard_src, guard_dst)
            rec(True, "触发层钩子 → hooks/", guard_dst)

    # ---------- 3. .gitignore ----------
    gi = os.path.join(target, ".gitignore")
    if os.path.isfile(gi):
        rec(True, ".gitignore", "已存在，跳过（不动你的内容）")
    elif dry:
        rec(True, ".gitignore", "将写入")
    else:
        with open(gi, "w", encoding="utf-8", newline="\n") as f:
            f.write(GITIGNORE)
        rec(True, ".gitignore", "已写入")

    # ---------- 4. 可选：git 版本库 ----------
    if args.init_git:
        if dry:
            rec(True, "git 版本库", "将 git init -b main + 首次提交")
        else:
            inside = repo_root(target)
            if inside:
                rec(True, "git 版本库", "已位于 git 仓库内（%s），跳过 init" % inside)
            else:
                try:
                    run(["git", "-C", target, "init", "-b", "main"])
                    run(["git", "-C", target, "add", "-A"])
                    c = run(["git", "-C", target, "commit", "-m",
                             "M-000 建立母版工作区版本库"])
                    if c.returncode == 0:
                        rec(True, "git 版本库", "已初始化 main 分支并首次提交")
                    else:
                        msg = (c.stderr or c.stdout or "").strip().splitlines()
                        rec(False, "git 版本库",
                            "init/add 成功但提交失败：%s｜先配 git user.name / user.email"
                            % (msg[-1] if msg else "未知原因"))
                except Exception as e:
                    rec(False, "git 版本库", str(e))

    # ---------- 5. 自验收 ----------
    vp = os.path.join(target, "verify.py")
    if dry:
        rec(True, "母版 verify.py 自验收", "DRY-RUN 跳过")
    elif not os.path.isfile(vp):
        rec(False, "母版 verify.py 自验收", "工作区根没有 verify.py")
    else:
        try:
            r = run([sys.executable, vp], cwd=target)
            tail = [l for l in r.stdout.splitlines() if l.startswith("验收结果")]
            ok = r.returncode == 0
            detail = tail[0] if tail else "退出码 %d" % r.returncode
            if not ok and "git 工作区干净" in r.stdout:
                detail += "｜提示：未提交变更（本步骤刚写完文件属正常，提交后即绿）"
            rec(ok, "母版 verify.py 自验收", detail)
        except Exception as e:
            rec(False, "母版 verify.py 自验收", str(e))

    return finish()


def finish():
    okn = sum(1 for ok, _, _ in results if ok)
    bad = [(t, d) for ok, t, d in results if not ok]
    print()
    print("=" * 62)
    print("整理结果: %d/%d PASS%s" % (okn, len(results),
                                  (", FAIL: " + "; ".join(t for t, _ in bad)) if bad else ""))
    print("=" * 62)
    if not bad:
        print("\n这个目录现在就是「顶层设计 / 母版工作区」，地位等同于老设备的 top_design。")
        print("\n日常怎么用：")
        print("  * 建新项目 —— 对 WorkBuddy 说：「给「XX 项目」建文档驱动架构」。")
        print("  * 改了母版 —— 跑 deploy-kit/sync-master.py（母版 → 技能模板 + 部署包副本）")
        print("                再跑 deploy-kit/package.py 重打分发 zip。")
        print("  * 验收母版 —— python verify.py（期望 35/35 PASS）。")
        print("\n纪律：母版是唯一权威源。别拿项目里的副本回头改母版，也别两台设备各改各的。")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
