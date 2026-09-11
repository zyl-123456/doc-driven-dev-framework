#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install.py —— 文档驱动开发架构 · 新设备一键部署

把本机跑通的整套「文档驱动开发架构」能力搬到一台新设备上，一次装齐四样：
  1. 行为层技能 doc-driven-dev            → ~/.workbuddy/skills/
  2. 移植技能 doc-driven-framework-porting（含 v4 模板） → ~/.workbuddy/skills/
  3. 触发层钩子 doc-driven-guard.py        → ~/.workbuddy/hooks/
  4. hooks 配置合并进 ~/.workbuddy/settings.json + 治理段追加进 ~/.workbuddy/MEMORY.md
  5. 母版全套（含 README 总说明）          → ~/.workbuddy/templates/doc-driven-master/

用法（在任意已装 WorkBuddy 的机器上，用任意 Python 3.8+ 执行）：
    python install.py                     # 正常安装
    python install.py --dry-run           # 只报告将做什么，不写盘
    python install.py --home <路径>        # 指定用户目录（默认 ~），用于测试
    python install.py --master-dir <路径>  # 指定母版安装位置
    python install.py --with-codebuddy    # 同时写 .codebuddy/settings.json（配置路径兜底）

设计原则：
  * **幂等**：重复执行不会重复挂钩子、不会重复追加记忆段；
  * **不破坏**：改动任何已有文件前先备份（.bak-<日期>）；
  * **可自检**：装完当场实测钩子脚本，输出真实结果，不靠"应该没问题"；
  * **解释器按本机探测**：钩子命令写入的是本机真实可用的 Python 绝对路径（跨设备直接拷
    settings.json 会因路径不存在而失效，所以必须在本机重新生成）。
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

try:  # Windows 控制台默认编码可能吞中文，强制 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PAYLOAD = os.path.join(HERE, "payload")
GUARD_NAME = "doc-driven-guard.py"
MEM_MARK = "开发项目治理（常设命令"
DATE = datetime.datetime.now().strftime("%Y%m%d")

results = []  # (ok, 标题, 说明)


def rec(ok, title, detail=""):
    results.append((ok, title, detail))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", title, (" —— " + detail) if detail else ""))


def step(n, text):
    print("\n" + "-" * 60)
    print("第 %s 步 · %s" % (n, text))
    print("-" * 60)


def backup(path):
    """改动前备份，返回备份路径。"""
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


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--home", default=os.path.expanduser("~"),
                    help="用户目录，默认 ~（主要给测试用）")
    ap.add_argument("--master-dir", default=None,
                    help="母版安装位置，默认 <home>/.workbuddy/templates/doc-driven-master")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写盘")
    ap.add_argument("--with-codebuddy", action="store_true",
                    help="同时写入 <home>/.codebuddy/settings.json（钩子配置路径兜底）")
    args = ap.parse_args()

    home = os.path.abspath(os.path.expanduser(args.home))
    wb = os.path.join(home, ".workbuddy")
    master_dir = args.master_dir or os.path.join(wb, "templates", "doc-driven-master")
    dry = args.dry_run

    print("=" * 60)
    print("文档驱动开发架构 · 新设备部署")
    print("=" * 60)
    print("用户目录  : %s" % home)
    print("WorkBuddy : %s" % wb)
    print("母版安装到: %s" % master_dir)
    print("Python    : %s" % sys.executable)
    print("模式      : %s" % ("DRY-RUN（不写盘）" if dry else "正式安装"))

    if sys.version_info < (3, 8):
        rec(False, "Python 版本 >= 3.8", "当前 %d.%d.%d" % sys.version_info[:3])
        return finish()

    # ---------- 第 0 步：检查 payload ----------
    step(0, "检查部署包完整性")
    needed = [
        "payload/skills/doc-driven-dev/SKILL.md",
        "payload/skills/doc-driven-framework-porting/SKILL.md",
        "payload/hooks/" + GUARD_NAME,
        "payload/memory-section.md",
        "payload/master/00-驱动开发规则.md",
        "payload/master/verify.py",
    ]
    missing = [p for p in needed if not os.path.isfile(os.path.join(HERE, p.replace("/", os.sep)))]
    rec(not missing, "部署包文件齐全", ("缺 %s" % ", ".join(missing)) if missing else "%d 项" % len(needed))
    if missing:
        return finish()

    # ---------- 第 1 步：自检钩子脚本（用 payload 原件，与是否写盘无关） ----------
    step(1, "自检钩子脚本（真实跑一遍，不靠「应该没问题」）")
    guard_src = os.path.join(PAYLOAD, "hooks", GUARD_NAME)
    fw_dir = os.path.join(PAYLOAD, "master")

    def run_guard(cwd):
        payload = json.dumps({"cwd": cwd, "hook_event_name": "UserPromptSubmit"})
        r = subprocess.run([sys.executable, guard_src], input=payload,
                           capture_output=True, text=True, encoding="utf-8", timeout=30)
        return json.loads(r.stdout)

    try:
        good = run_guard(fw_dir)
        ctx = (good.get("hookSpecificOutput") or {}).get("additionalContext", "")
        rec(bool(ctx) and good.get("continue") is True,
            "框架项目 → 注入纪律提醒", (ctx[:38] + "…") if ctx else "未注入")
    except Exception as e:
        rec(False, "框架项目 → 注入纪律提醒", "钩子执行异常: %s" % e)

    tmp = tempfile.mkdtemp()
    try:
        plain = run_guard(tmp)
        rec(plain.get("continue") is True and not (plain.get("hookSpecificOutput") or {}).get("additionalContext"),
            "非框架项目 → 静默放行", "不打扰无关工作")
    except Exception as e:
        rec(False, "非框架项目 → 静默放行", "钩子执行异常: %s" % e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ---------- 第 2 步：安装技能 ----------
    step(2, "安装两个用户级技能")
    if not dry:
        os.makedirs(os.path.join(wb, "skills"), exist_ok=True)
    for name in ("doc-driven-dev", "doc-driven-framework-porting"):
        src = os.path.join(PAYLOAD, "skills", name)
        dst = os.path.join(wb, "skills", name)
        try:
            if dry:
                rec(True, "技能 %s" % name, "将安装到 %s" % dst)
                continue
            bk = None
            if os.path.isdir(dst):
                bk = backup(dst)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            n = sum(len(f) for _, _, f in os.walk(dst))
            rec(os.path.isfile(os.path.join(dst, "SKILL.md")),
                "技能 %s" % name, "%d 个文件%s" % (n, "，旧版已备份" if bk else ""))
        except Exception as e:
            rec(False, "技能 %s" % name, str(e))

    # ---------- 第 3 步：安装钩子脚本 ----------
    step(3, "安装触发层钩子")
    hooks_dir = os.path.join(wb, "hooks")
    guard_dst = os.path.join(hooks_dir, GUARD_NAME)
    try:
        if dry:
            rec(True, "钩子脚本", "将安装到 %s" % guard_dst)
        else:
            os.makedirs(hooks_dir, exist_ok=True)
            shutil.copy2(guard_src, guard_dst)
            rec(os.path.isfile(guard_dst), "钩子脚本", guard_dst)
    except Exception as e:
        rec(False, "钩子脚本", str(e))

    # ---------- 第 4 步：把 hooks 配置合并进 settings.json ----------
    step(4, "合并 hooks 配置（保留原有配置，幂等）")
    # 钩子命令必须用本机真实可用的解释器绝对路径
    hook_cmd = '"%s" "%s"' % (sys.executable.replace("\\", "/"),
                              guard_dst.replace("\\", "/"))

    targets = [os.path.join(wb, "settings.json")]
    if args.with_codebuddy:
        targets.append(os.path.join(home, ".codebuddy", "settings.json"))

    for sp in targets:
        existed = os.path.isfile(sp)
        data = {}
        if existed:
            try:
                with open(sp, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                rec(False, "settings.json 合并 (%s)" % sp,
                    "不是合法 JSON，已跳过且未改动原文件: %s" % e)
                continue
        hooks = data.setdefault("hooks", {})
        added = []
        for event, matcher in (("SessionStart", "startup"), ("UserPromptSubmit", None)):
            arr = hooks.setdefault(event, [])
            dup = any(GUARD_NAME in h.get("command", "")
                      for m in arr if isinstance(m, dict)
                      for h in m.get("hooks", []) if isinstance(h, dict))
            if dup:
                continue
            entry = {"hooks": [{"type": "command", "command": hook_cmd, "timeout": 10}]}
            if matcher:
                entry["matcher"] = matcher
            arr.append(entry)
            added.append(event)

        if not added:
            label = os.path.basename(os.path.dirname(sp)) or sp
            rec(True, "settings.json 合并 (%s)" % label, "钩子已存在，跳过（幂等）")
            continue
        if dry:
            rec(True, "settings.json 合并", "将新增事件: %s" % ", ".join(added))
            continue
        try:
            os.makedirs(os.path.dirname(sp), exist_ok=True)
            bk = backup(sp) if existed else None
            with open(sp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            rec(True, "settings.json 合并", "新增 %s%s" % (", ".join(added), "，已备份" if bk else "（新建）"))
        except Exception as e:
            rec(False, "settings.json 合并", str(e))

    # ---------- 第 5 步：安装母版 + 追加治理记忆段 ----------
    step(5, "安装母版全套 + 追加治理记忆段")
    try:
        if dry:
            rec(True, "母版安装", "将安装到 %s" % master_dir)
        else:
            shutil.copytree(os.path.join(PAYLOAD, "master"), master_dir, dirs_exist_ok=True)
            n = sum(len(f) for _, _, f in os.walk(master_dir))
            rec(n >= 8, "母版安装", "%s（%d 个文件）" % (master_dir, n))
    except Exception as e:
        rec(False, "母版安装", str(e))

    mem_path = os.path.join(wb, "MEMORY.md")
    try:
        with open(os.path.join(PAYLOAD, "memory-section.md"), "r", encoding="utf-8") as f:
            section = f.read().strip()
        old = ""
        if os.path.isfile(mem_path):
            with open(mem_path, "r", encoding="utf-8") as f:
                old = f.read()
        if MEM_MARK in old:
            rec(True, "治理记忆段", "已存在，跳过（幂等）")
        elif dry:
            rec(True, "治理记忆段", "将追加到 %s" % mem_path)
        else:
            bk = backup(mem_path) if old else None
            os.makedirs(os.path.dirname(mem_path), exist_ok=True)
            with open(mem_path, "w", encoding="utf-8") as f:
                f.write((old.rstrip() + "\n\n" if old.strip() else "# 用户级长期记忆（跨项目）\n\n")
                        + section + "\n")
            rec(True, "治理记忆段", "已追加%s" % ("，原文件已备份" if bk else ""))
    except Exception as e:
        rec(False, "治理记忆段", str(e))

    # ---------- 第 6 步：安装后核对 ----------
    step(6, "安装后核对")
    if dry:
        rec(True, "安装后核对", "DRY-RUN 模式跳过")
    else:
        checks = [
            (os.path.join(wb, "skills", "doc-driven-dev", "SKILL.md"), "技能 doc-driven-dev"),
            (os.path.join(wb, "skills", "doc-driven-framework-porting", "templates", "verify.py"),
             "移植技能模板"),
            (guard_dst, "钩子脚本"),
            (os.path.join(master_dir, "00-驱动开发规则.md"), "母版 00 规则"),
        ]
        for p, label in checks:
            rec(os.path.isfile(p), "已就位: %s" % label)
        try:
            with open(os.path.join(wb, "settings.json"), "r", encoding="utf-8") as f:
                cfg = json.load(f)
            rec("hooks" in cfg and "UserPromptSubmit" in cfg.get("hooks", {}),
                "已就位: settings.json 钩子配置")
        except Exception as e:
            rec(False, "已就位: settings.json 钩子配置", str(e))
        # 母版自验收
        try:
            r = subprocess.run([sys.executable, os.path.join(master_dir, "verify.py")],
                               cwd=master_dir, capture_output=True, text=True,
                               encoding="utf-8", timeout=60)
            tail = [l for l in r.stdout.splitlines() if l.startswith("验收结果")]
            ok = r.returncode == 0
            detail = tail[0] if tail else "退出码 %d" % r.returncode
            # 若母版被装进某个 git 仓库内部（例如测试时装到项目子目录），
            # "工作区干净"一项会受宿主仓库的未提交变更影响 —— 属环境因素，不是安装失败。
            if not ok and "git 工作区干净" in r.stdout:
                detail += "｜提示：母版位于某个 git 仓库内，该项受宿主仓库未提交变更影响（环境因素）"
            rec(ok, "母版 verify.py 自验收", detail)
        except Exception as e:
            rec(False, "母版 verify.py 自验收", str(e))

    return finish()


def finish():
    okn = sum(1 for ok, _, _ in results if ok)
    bad = [(t, d) for ok, t, d in results if not ok]
    print()
    print("=" * 60)
    print("部署结果: %d/%d PASS%s" % (okn, len(results),
                                    (", FAIL: " + "; ".join(t for t, _ in bad)) if bad else ""))
    print("=" * 60)
    if bad:
        print("\n未通过项：")
        for t, d in bad:
            print("  - %s%s" % (t, ("（%s）" % d) if d else ""))
    else:
        print("\n下一步：")
        print("  1. 重启 WorkBuddy（或开一个新会话），让钩子配置生效；")
        print("  2. 在任意项目里发一条消息，观察上下文是否出现「[文档驱动框架]」提醒；")
        print("  3. 若没有生效，用 --with-codebuddy 重跑一次（钩子配置路径兜底）；")
        print("  4. 【可选但推荐】把本包整理成「母版工作区」（顶层设计目录）：")
        print("     python init-master-workspace.py --init-git")
        print("     之后新项目都从这个母版取源，改母版后跑 sync-master.py 即可保持各副本同步；")
        print("  5. 新项目开工：对 WorkBuddy 说「给 XX 项目建文档驱动架构」。")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
