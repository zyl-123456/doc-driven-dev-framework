#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify.py · {{PROJECT}} —— 总验收命令（文档驱动开发框架 v3 通用版）

设计依据：开发驱动文档/00-驱动开发规则.md 第八节「总验收命令」六项要求
  1. 人类可独立执行：命令输出即结论，不依赖 AI 转述
  2. 失败必须显式：任一关键项失败返回非零退出码
  3. 硬事实可验证：文档里的可量化声明必须能被本命令对账
  4. 覆盖安全边界：00 文档第十一节 SEC 条款纳入检查
  5. 自检运行环境：前置校验解释器版本
  6. 结论绑定输入版本：输出 git commit 哈希（若有）

用法：
  python verify.py                              # 通用检查
  E:\\anaconda\\python.exe verify.py             # Windows 工作站推荐口径

版本：v3.0.0（模板母版 2026-09-12）
说明：本脚本与项目无关，复制到新项目后无需改动即可运行；项目专属检查项
      写在文件末尾「领域扩展检查区」，按提示增删即可。
"""

import os
import re
import subprocess
import sys

# ============================================================
# 可调开关
# ============================================================

# 文档目录探测顺序（按需增删；脚本会取第一个真正含 00 文档的目录）
DOC_DIR_CANDIDATES = ["开发驱动文档", ".", "docs/开发驱动文档", "文档/开发驱动文档"]

# 是否把"占位符未清零"视为失败。
# 模板母版工作区保持 False（母版本就该有占位符）；项目副本建议改 True。
STRICT_PLACEHOLDER = False

# 强制要求存在的最小里程碑 / 设计编号（留空则不检查具体编号）
REQUIRED_MILESTONE = "M-000"
REQUIRED_DESIGN = "D-000"

GOV_FILENAMES = [
    "00-驱动开发规则.md",
    "01-人类需求描述.md",
    "02-需求技术拆解.md",
    "03-技术实现方案.md",
    "04-实现过程记录.md",
]

# 00 文档必须具备的核心章节（按关键词检查，抗重编号）
RULES_SECTIONS = [
    "这套框架解决什么问题",
    "核心机制",
    "五文档体系",
    "编号引用体系",
    "闭环工作流",
    "落档纪律",
    "证据裁决规则",
    "对账验收",
    "文档生命周期",
    "权责",
    "安全底线与交付纪律",
    "领域扩展",
]

# ============================================================
# 环境自检（要求 5，前置）
# ============================================================

if sys.version_info < (3, 8):
    print("[ENV] FAIL: 需要 Python >= 3.8，当前 %d.%d.%d" % sys.version_info[:3])
    sys.exit(1)
print("[ENV] PASS: Python %d.%d.%d" % sys.version_info[:3])

BASE = os.path.dirname(os.path.abspath(__file__))

passed = 0
failed = 0
fail_items = []


def check(name, ok, detail=""):
    global passed, failed
    tag = "PASS" if ok else "FAIL"
    print("[%s] %s%s" % (tag, name, (" —— " + detail) if detail else ""))
    if ok:
        passed += 1
    else:
        failed += 1
        fail_items.append(name)


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------- 定位文档目录 ----------

DOC = None
for cand in DOC_DIR_CANDIDATES:
    p = os.path.normpath(os.path.join(BASE, cand))
    if os.path.isfile(os.path.join(p, GOV_FILENAMES[0])):
        DOC = p
        break

if DOC is None:
    print("[ENV] FAIL: 找不到文档目录（以下位置均无 %s）：%s"
          % (GOV_FILENAMES[0], ", ".join(DOC_DIR_CANDIDATES)))
    sys.exit(1)

rel = os.path.relpath(DOC, BASE).replace("\\", "/")
print("[ENV] PASS: 文档目录 = %s" % ("<项目根>" if rel == "." else rel))
print()

# ============================================================
# 1. 文档结构对账
# ============================================================

for gf in GOV_FILENAMES:
    p = os.path.join(DOC, gf)
    check("文档存在且非空: %s" % gf, os.path.isfile(p) and os.path.getsize(p) > 0)

# 根入口四层结构
sh_path = os.path.join(BASE, "START_HERE.md")
if not os.path.isfile(sh_path):
    check("根入口 START_HERE.md 存在", False, "必须在项目根目录")
    sh = ""
else:
    sh = read(sh_path)
    check("根入口 START_HERE.md 存在", True)
check("根入口四层阅读路径完整",
      all(k in sh for k in ["第一层", "第二层", "第三层", "第四层"]),
      "缺层会导致新会话无法按需下钻")

# 00 规则文档核心章节齐全
rules = read(os.path.join(DOC, GOV_FILENAMES[0]))
for sec in RULES_SECTIONS:
    check("00 规则章节存在: %s" % sec, sec in rules)

# ============================================================
# 2. 硬条款对账（安全底线 + 交付纪律 + 协作授权）
# ============================================================

check("安全底线条款 SEC-001~004 齐全",
      all(("SEC-%03d" % i) in rules for i in range(1, 5)),
      "条款缺失 = 00 文档第十一节被破坏")

req = read(os.path.join(DOC, GOV_FILENAMES[1]))
check("01 交付纪律 C-002 已登记", "C-002" in req)
check("01 协作授权声明存在", "协作模式授权" in req and "AI 全权负责" in req,
      "缺授权声明会导致后续技术决策反复请示")

# ============================================================
# 3. 跨文档编号一致性（悬空引用检测）
# ============================================================

tech = read(os.path.join(DOC, GOV_FILENAMES[2]))
plan = read(os.path.join(DOC, GOV_FILENAMES[3]))
log = read(os.path.join(DOC, GOV_FILENAMES[4]))


def ids(text, prefix):
    # 负向断言：避免把 REQ-001 里的 "Q-001"、ASM-000 里的 "M-000" 误判成独立编号
    return set(re.findall(r"(?<![A-Za-z])" + prefix + r"-\d{3}", text))


q_in_01 = ids(req, "Q")
q_in_02 = ids(tech, "Q")
dangling_q = q_in_01 - q_in_02
check("01 的 Q 编号在 02 均有登记", not dangling_q,
      ("悬空: %s" % ",".join(sorted(dangling_q))) if dangling_q else "")

asm_in_02 = ids(tech, "ASM")
asm_in_04 = ids(log, "ASM")
dangling_asm = asm_in_02 - asm_in_04
check("02 的 ASM 编号在 04 假设登记簿均有登记", not dangling_asm,
      ("悬空: %s" % ",".join(sorted(dangling_asm))) if dangling_asm else "")

d_in_03 = ids(plan, "D")
if REQUIRED_DESIGN:
    check("03 含关键设计 %s" % REQUIRED_DESIGN, REQUIRED_DESIGN in d_in_03)
else:
    check("03 至少含一条关键设计 D-xxx", bool(d_in_03), "编号即索引，缺编号等于设计无法被引用")

m_in_04 = ids(log, "M")
if REQUIRED_MILESTONE:
    check("04 含里程碑 %s" % REQUIRED_MILESTONE, REQUIRED_MILESTONE in m_in_04)
else:
    check("04 至少含一条里程碑 M-xxx", bool(m_in_04))
check("04 坑位速查表存在", "坑位速查表" in log, "跨会话排错的入口，缺了会重复踩坑")

check("REQ 采用 EARS 句式（01 含触发/响应结构）",
      ("触发条件" in req and "系统响应" in req) or "当" in req,
      "模糊表述无法验收")

# ============================================================
# 4. 占位符残留（模板复制到新项目后应清零）
# ============================================================

holders = set()
for gf in GOV_FILENAMES:
    holders |= set(re.findall(r"\{\{[^}]{1,40}\}\}", read(os.path.join(DOC, gf))))
if os.path.isfile(sh_path):
    holders |= set(re.findall(r"\{\{[^}]{1,40}\}\}", sh))

if holders:
    msg = "剩余占位符 %d 种: %s" % (
        len(holders), ", ".join(sorted(holders)[:6]) + (" …" if len(holders) > 6 else ""))
    if STRICT_PLACEHOLDER:
        check("占位符已全部清零", False, msg)
    else:
        print("[INFO] 占位符检查：%s（模板母版属正常；项目副本可把 STRICT_PLACEHOLDER 改为 True）" % msg)
else:
    check("占位符已全部清零", True)

# ============================================================
# 5. 版本库卫生（落档纪律第 2 条）
# ============================================================


def git(args):
    try:
        r = subprocess.run(["git"] + args, cwd=BASE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=15)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception:
        return None, ""


rc, out = git(["rev-parse", "--is-inside-work-tree"])
if rc == 0 and out.strip() == "true":
    rc2, head = git(["rev-parse", "--short", "HEAD"])
    print("[INFO] git HEAD: %s" % head.strip() if rc2 == 0 else "[INFO] git HEAD: <无提交>")

    rc3, st = git(["status", "--porcelain"])
    dirty = [l for l in st.splitlines() if l.strip()]
    if rc2 == 0:
        check("git 工作区干净（任务完成判定）", not dirty,
              ("未提交变更 %d 项，视为任务未完成" % len(dirty)) if dirty else "")
    else:
        print("[INFO] 尚无提交，工作区干净性检查跳过（首提交后生效）")
else:
    print("[INFO] 当前目录非 git 仓库，版本库卫生检查跳过")

# ============================================================
# 6. 领域扩展检查区（项目专属，按需增删）
# ============================================================
# 复制到新项目后，在这里补项目自己的硬检查，例如：
#
#   check("权限白名单未超范围",
#         not re.search(r"android.permission.(CAMERA|CONTACTS)", manifest_text))
#   check("01 的阈值参数表已量化", "待量化" not in req)
#
# 保持"每条检查都能被人类一眼看懂、失败即非零退出"即可。

# ============================================================
# 汇总（要求 2：失败显式）
# ============================================================

print()
total = passed + failed
print("=" * 52)
print("验收结果: %d/%d PASS%s" % (
    passed, total,
    (", FAIL %d 项: %s" % (failed, "; ".join(fail_items))) if failed else ""))
print("=" * 52)
sys.exit(0 if failed == 0 else 1)
