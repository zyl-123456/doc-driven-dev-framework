#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
package.py —— 把 deploy-kit 打成可分发的包，放进 dist/

一次产出两种格式：
    *.zip      通用；但中文文件名靠 ZIP 的"UTF-8 标志位"约定，
               老版 Info-ZIP unzip / 某些 macOS 工具会忽略它 → 解出乱码名。
    *.tar.gz   中文文件名更稳（tar 按 UTF-8 直接存，无标志位历史包袱），
               macOS / Linux / Windows 10+ 自带 tar 都能正确解开。
               Windows↔macOS 之间传含中文名的包，优先用它。

为什么要脚本化：
    手工打包有两个老毛病：容易漏文件、容易把 __pycache__ / .bak 打进去。
    这和 sync-master.py 的动机一样——「重复且易错」的动作，固化成一条命令。

正确顺序（漏了第一步，包里就是旧版）：
    1. python sync-master.py         # 母版 / 技能 / 钩子 / 模板副本先同步
    2. python package.py             # 再打包

用法：
    python package.py                 # 版本号自动从 deploy-kit README 探测
    python package.py --version v4    # 手动指定版本号
    python package.py --out <路径>    # 指定输出（默认 dist/doc-driven-kit-<ver>-<日期>.zip，另出同名 .tar.gz）
"""

import argparse
import datetime
import os
import re
import sys
import tarfile
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(os.path.dirname(HERE), "dist")
KIT_NAME = "deploy-kit"          # zip 内顶层目录名（解压即得 deploy-kit/…）
README = os.path.join(HERE, "README-新设备部署.md")
EXCLUDE_DIRS = {"__pycache__", ".git", ".workbuddy", "dist"}


def detect_version():
    """从部署说明头部探测「包版本：vX」。"""
    try:
        with open(README, "r", encoding="utf-8") as f:
            m = re.search(r"包版本[：:]\s*(v[\d.]+)", f.read())
        if m:
            return m.group(1)
    except Exception:
        pass
    return "v0"


def skip(name):
    return (name.endswith((".pyc", ".bak", ".tmp"))
            or ".bak-" in name or name.startswith("."))


def collect():
    """返回 [(绝对路径, zip内相对路径)]，顶层统一加 deploy-kit/ 前缀。"""
    items = []
    for r, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fn in sorted(files):
            if skip(fn):
                continue
            ap = os.path.join(r, fn)
            rel = os.path.relpath(ap, os.path.dirname(HERE)).replace("\\", "/")
            if rel.startswith(KIT_NAME + "/"):
                items.append((ap, rel))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=None, help="版本号，默认从 README 探测")
    ap.add_argument("--out", default=None, help="输出 zip 路径")
    args = ap.parse_args()

    ver = args.version or detect_version()
    date = datetime.datetime.now().strftime("%Y%m%d")
    out = args.out or os.path.join(DIST, "doc-driven-kit-%s-%s.zip" % (ver, date))

    items = collect()
    if not items:
        print("FAIL 没收集到任何文件，确认 deploy-kit/ 目录是否正确")
        return 1

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for ap_, rel in items:
            z.write(ap_, rel)

    # 同时打一份 tar.gz —— 中文文件名的"根治"格式。
    # 原因：ZIP 对非 ASCII 名字靠"UTF-8 标志位"(bit 11)约定，规范的包也会被
    # 老版 Info-ZIP unzip / 某些 macOS 工具忽略标志位而解出乱码名；
    # tar 没有这个历史包袱，macOS/Linux/Windows(10+) 自带的 tar 都按 UTF-8 处理。
    tgz = out[:-4] + ".tar.gz"
    with tarfile.open(tgz, "w:gz", format=tarfile.PAX_FORMAT) as t:
        for ap_, rel in items:
            t.add(ap_, arcname=rel)

    size = os.path.getsize(out)
    tsize = os.path.getsize(tgz)
    print("=" * 60)
    print("打包完成")
    print("=" * 60)
    print("版本  : %s" % ver)
    print("文件数: %d" % len(items))
    print("ZIP   : %s（%.1f KB）" % (out, size / 1024.0))
    print("TAR.GZ: %s（%.1f KB）" % (tgz, tsize / 1024.0))
    print("        ↑ 跨平台（尤其 Windows↔macOS）传中文文件名的包，优先用这个")
    # 兼容性核对：确认钩子副本已在包内
    if not any(rel.endswith("payload/hooks/doc-driven-guard.py") for _, rel in items):
        print("\n⚠ 包里没有 payload/hooks/doc-driven-guard.py —— 先跑 sync-master.py")
        return 1
    others = [f for f in os.listdir(DIST)
              if (f.endswith(".zip") or f.endswith(".tar.gz"))
              and os.path.join(DIST, f) not in (out, tgz)] \
        if os.path.isdir(DIST) else []
    if others:
        print("\n注意：dist/ 里还有其它旧包，可按需清理：%s" % ", ".join(sorted(others)))
    print("\n下一步：把包拷到新设备解压，然后跑 python install.py")
    print("       macOS 上若 zip 解出乱码文件名，请用：")
    print("       python3 -c \"import zipfile; zipfile.ZipFile('%s').extractall('.')\""
          % os.path.basename(out))
    print("       或直接改用 tar.gz：tar -xzf %s" % os.path.basename(tgz))
    return 0


if __name__ == "__main__":
    sys.exit(main())
