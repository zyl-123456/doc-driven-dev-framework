#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync-master.py —— 把母版工作区与技能的最新内容同步到部署包副本

为什么需要这个脚本：
    多副本是这套框架唯一的结构性风险点。母版一改，发布副本就滞后；
    新设备装到旧版，于是又出现「文档说 A、现实是 B」。
    手工 cp 容易漏文件、也容易漏比对，所以把它固化成一条命令。

它管四条链路：
    1. 母版目录 → deploy-kit/payload/master/          （母版发布副本）
    2. 本机技能 → deploy-kit/payload/skills/          （技能发布副本）
    3. 母版 hooks/ → deploy-kit/payload/hooks/        （触发层钩子发布副本）
    4. 副本回推与告警（两条）：
       a. 母版 → 技能 templates/  （先把技能模板顶到最新，防"建新项目拿到旧模板"）
       b. 母版 hooks/ ↔ 本机实装钩子 告警（防母版改了钩子却没重装）

用法：
    python sync-master.py                     # 比对并同步
    python sync-master.py --check             # 只比对报告，不写盘
    python sync-master.py --master <路径>      # 指定母版目录（默认 deploy-kit 上一级）
    python sync-master.py --skills-src <路径>  # 指定本机技能目录（默认 ~/.workbuddy/skills）
"""

import argparse
import filecmp
import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PAYLOAD = os.path.join(HERE, "payload")
PAYLOAD_MASTER = os.path.join(HERE, "payload", "master")
PAYLOAD_SKILLS = os.path.join(HERE, "payload", "skills")
SKILL_NAMES = ("doc-driven-dev", "doc-driven-framework-porting")
SEVEN = ["00-驱动开发规则.md", "01-人类需求描述.md", "02-需求技术拆解.md",
         "03-技术实现方案.md", "04-实现过程记录.md", "START_HERE.md", "verify.py"]
EXCLUDE_DIRS = {"__pycache__", ".git", ".workbuddy"}


def skip(name):
    return (name.endswith((".pyc", ".bak", ".tmp"))
            or ".bak-" in name or name.startswith("."))


def tree(root):
    """返回 {相对路径: 绝对路径}，过滤缓存与备份。"""
    out = {}
    if not os.path.isdir(root):
        return out
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if skip(f):
                continue
            p = os.path.join(r, f)
            out[os.path.relpath(p, root)] = p
    return out


def flat(root):
    """只取根下的一层文件（母版目录用）。"""
    out = {}
    if not os.path.isdir(root):
        return out
    for n in sorted(os.listdir(root)):
        p = os.path.join(root, n)
        if os.path.isfile(p) and n.lower().endswith((".md", ".py")):
            out[n] = p
    return out


def compare(src, dst, label):
    """比对两个 {相对路径: 绝对路径} 映射。"""
    same, lag, orphan = [], [], []
    for rel, sp in src.items():
        dp = dst.get(rel)
        if dp is None or not filecmp.cmp(sp, dp, shallow=False):
            lag.append(rel)
        else:
            same.append(rel)
    orphan = [rel for rel in dst if rel not in src]
    return same, lag, orphan


def sync(src_map, dst_root, lag, dry):
    if dry:
        return 0
    for rel in lag:
        dp = os.path.join(dst_root, rel)
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        shutil.copy2(src_map[rel], dp)
    return len(lag)


def report(label, src_root, dst_root, dry):
    src, dst = tree(src_root), tree(dst_root)
    same, lag, orphan = compare(src, dst, label)
    print("\n【%s】" % label)
    print("  源: %s" % src_root)
    print("  目标: %s" % dst_root)
    for rel in sorted(same):
        print("    一致   %s" % rel)
    for rel in sorted(lag):
        print("    待同步 %s" % rel)
    for rel in sorted(orphan):
        print("    副本多出 %s（源已无此文件，不自动删）" % rel)
    if not lag:
        print("  结论：一致（%d 份）" % len(same))
    elif dry:
        print("  结论：%d 份待同步（--check 未写盘）" % len(lag))
    else:
        n = sync(src, dst_root, lag, False)
        print("  结论：已同步 %d 份" % n)
    return len(same), len(lag), len(orphan)


def sync_templates(master_dir, skills_root, dry):
    """把母版七件套推送到技能 templates/（母版 = 唯一权威源，副本跟随）。

    为什么是"自动推"而不是"只告警"：
        移植技能建新项目时，取源就是技能自带的 templates/。
        母版改了却不同步 templates/，建出来的新项目就带着旧模板 ——
        而用户看到的却是"我从母版建的"，属于隐性漂移。
        所以这里在同步模式下直接覆盖（副本方向永远是 母版 → 各副本）。
    """
    tpl = os.path.join(skills_root, "doc-driven-framework-porting", "templates")
    if not os.path.isdir(tpl):
        print("\n【母版 → 技能 templates/】\n  跳过：未找到 %s（技能未装？）" % tpl)
        return 0
    lag = []
    for n in SEVEN:
        a, b = os.path.join(master_dir, n), os.path.join(tpl, n)
        if not os.path.isfile(b) or not filecmp.cmp(a, b, shallow=False):
            lag.append(n)
    print("\n【母版 → 技能 templates/】")
    if not lag:
        print("  ✓ 技能 templates/ 与母版七件套完全一致（%d 份）" % len(SEVEN))
        return 0
    if dry:
        print("  %d 份待同步：%s" % (len(lag), ", ".join(lag)))
        print("  结论：--check 未写盘（正式跑会推送到 %s）" % tpl)
        return len(lag)
    for n in lag:
        shutil.copy2(os.path.join(master_dir, n), os.path.join(tpl, n))
    print("  已同步 %d 份 → %s" % (len(lag), tpl))
    print("  （母版是唯一权威源；技能 templates/ 是发布副本，永远跟随母版）")
    return len(lag)


def check_hook(master_dir, home_dir):
    """告警：本机实装钩子是否落后于母版 hooks/。
    实装钩子才是真正每轮跑的代码 —— 母版改了钩子却没重装，等于白改。"""
    mh = os.path.join(master_dir, "hooks", "doc-driven-guard.py")
    lh = os.path.join(home_dir, ".workbuddy", "hooks", "doc-driven-guard.py")
    print("\n【母版 hooks/ ↔ 本机实装钩子 一致性】")
    if not os.path.isfile(lh):
        print("  ⚠ 本机未装钩子（%s）—— 请跑 install.py 安装" % lh)
        return 1
    if not os.path.isfile(mh):
        print("  跳过：母版无 hooks/doc-driven-guard.py")
        return 0
    if filecmp.cmp(mh, lh, shallow=False):
        print("  ✓ 本机实装钩子与母版一致")
        return 0
    print("  ⚠ 本机实装钩子落后于母版：%s" % lh)
    print("    请重跑 install.py（或手动覆盖）让母版钩子生效")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default=os.path.dirname(HERE),
                    help="母版目录，默认 deploy-kit 的上一级")
    ap.add_argument("--skills-src", default=os.path.join(
        os.path.expanduser("~"), ".workbuddy", "skills"),
        help="本机技能目录，默认 ~/.workbuddy/skills")
    ap.add_argument("--check", action="store_true", help="只比对，不写盘")
    args = ap.parse_args()

    master = os.path.abspath(args.master)
    skills_src = os.path.abspath(os.path.expanduser(args.skills_src))
    dry = args.check

    print("=" * 62)
    print("部署包副本同步  %s" % ("（--check 只报告）" if dry else ""))
    print("=" * 62)

    if not os.path.isdir(master):
        print("FAIL 母版目录不存在: %s" % master)
        return 1

    # 链路 1：母版 → payload/master（只取母版根下一层 md/py）
    src = flat(master)
    dst = flat(PAYLOAD_MASTER)
    same, lag, orphan = compare(src, dst, "master")
    print("\n【母版 → payload/master】")
    print("  源: %s" % master)
    for rel in sorted(same):
        print("    一致   %s" % rel)
    for rel in sorted(lag):
        print("    待同步 %s" % rel)
    for rel in sorted(orphan):
        print("    副本多出 %s（母版已无此文件，不自动删）" % rel)
    if not lag:
        print("  结论：一致（%d 份）" % len(same))
    elif dry:
        print("  结论：%d 份待同步（--check 未写盘）" % len(lag))
    else:
        n = 0
        for rel in lag:
            shutil.copy2(src[rel], os.path.join(PAYLOAD_MASTER, rel))
            n += 1
        print("  结论：已同步 %d 份" % n)

    # 链路 2：本机技能 → payload/skills
    for name in SKILL_NAMES:
        s = os.path.join(skills_src, name)
        d = os.path.join(PAYLOAD_SKILLS, name)
        if not os.path.isdir(s):
            print("\n【技能 %s】\n  跳过：本机未安装 %s" % (name, s))
            continue
        report("技能 %s" % name, s, d, dry)

    # 链路 3：母版 hooks/ → payload/hooks（触发层钩子，绝不能锁在旧版）
    report("母版 hooks → payload/hooks",
           os.path.join(master, "hooks"), os.path.join(PAYLOAD, "hooks"), dry)

    # 链路 4：一致性告警（模板 + 实装钩子）
    tpl_lag = sync_templates(master, skills_src, dry)
    hook_lag = check_hook(master, os.path.expanduser("~"))

    print("\n" + "=" * 62)
    print("下一步：重新打包 deploy-kit（否则 dist/ 里的 zip 仍是旧版）。")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
