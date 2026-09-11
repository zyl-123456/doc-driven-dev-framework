#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync-master.py —— 把母版工作区的最新内容同步到部署包副本

为什么需要这个脚本：
    deploy-kit/payload/master/ 是母版工作区的**发布副本**。母版一改，
    副本就滞后；新设备装到的是旧版，于是又出现「文档说 A、现实是 B」。
    手工 cp 容易漏文件、也容易漏比对，所以把它固化成一条命令。

同步范围：
    母版目录根下的全部 .md 与 .py 文件（即「框架本体八件套 + 理解材料两份」）。
    不含子目录（deploy-kit / _archive / dist / .workbuddy 都是母版工作区专有，
    不属于分发内容）。

用法：
    python sync-master.py              # 比对差异并同步
    python sync-master.py --check      # 只比对报告，不写盘（可当体检用）
    python sync-master.py --master <路径>   # 指定母版目录（默认取 deploy-kit 的上一级）
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
PAYLOAD_MASTER = os.path.join(HERE, "payload", "master")


def collect(master_dir):
    names = []
    for n in sorted(os.listdir(master_dir)):
        p = os.path.join(master_dir, n)
        if os.path.isfile(p) and n.lower().endswith((".md", ".py")):
            names.append(n)
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default=os.path.dirname(HERE),
                    help="母版目录，默认 deploy-kit 的上一级")
    ap.add_argument("--check", action="store_true", help="只比对，不写盘")
    args = ap.parse_args()

    master = os.path.abspath(args.master)
    if not os.path.isdir(master):
        print("FAIL 母版目录不存在: %s" % master)
        return 1
    if not os.path.isdir(PAYLOAD_MASTER):
        print("FAIL 副本目录不存在: %s" % PAYLOAD_MASTER)
        return 1

    print("母版: %s" % master)
    print("副本: %s" % PAYLOAD_MASTER)
    print("-" * 60)

    src_names = collect(master)
    dst_names = collect(PAYLOAD_MASTER)

    lag, same, orphan = [], [], []
    for n in src_names:
        s, d = os.path.join(master, n), os.path.join(PAYLOAD_MASTER, n)
        if not os.path.isfile(d):
            lag.append(n)
        elif filecmp.cmp(s, d, shallow=False):
            same.append(n)
        else:
            lag.append(n)
    orphan = [n for n in dst_names if n not in src_names]

    for n in same:
        print("  一致   %s" % n)
    for n in lag:
        print("  待同步 %s" % n)
    for n in orphan:
        print("  副本多出 %s（母版已无此文件）" % n)

    print("-" * 60)
    print("共 %d 份：一致 %d，待同步 %d，副本多出 %d"
          % (len(src_names), len(same), len(lag), len(orphan)))

    if not lag and not orphan:
        print("\n结论：副本已与母版一致，无需动作。")
        return 0
    if args.check:
        print("\n结论：检出差异（--check 模式，未写盘）。去掉 --check 即可同步。")
        return 1

    for n in lag:
        shutil.copy2(os.path.join(master, n), os.path.join(PAYLOAD_MASTER, n))
    print("\n已同步 %d 份。" % len(lag))
    if orphan:
        print("注意：副本多出的文件未自动删除，请人工确认——")
        for n in orphan:
            print("  %s" % os.path.join(PAYLOAD_MASTER, n))
    print("\n下一步：重新打包 deploy-kit（否则 dist/ 里的 zip 仍是旧版）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
