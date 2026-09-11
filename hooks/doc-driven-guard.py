#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doc-driven-guard.py —— 文档驱动开发框架「防忽略」钩子（v2 · 实时读文档版）

挂载位置：WorkBuddy 用户级配置 ~/.workbuddy/settings.json 的 hooks 字段
  事件一：SessionStart     —— 新会话：注入从项目 00 文档实时提取的纪律 + 项目当前快照
  事件二：UserPromptSubmit —— 每次提问：注入项目「当前快照」一行（动态内容，非固定复读）

它解决什么问题：
  框架文件躺在项目里，AI 不主动读就等于不存在。本钩子由平台在每次会话/提问时
  强制调用，把框架纪律直接塞进 AI 的输入上下文，绕不过去。

v2 相对 v1 的关键变化（消除内嵌副本）：
  v1 把纪律文字**内嵌**在脚本里 —— 改母版（00 文档）不会自动同步，
  形成"脚本副本 vs 母版"的漂移风险（正是框架自己最反对的病）。
  v2 改为**实时读项目里的 00 文档**并按章节提取要点：母版一改立即生效，零同步成本。
  仅当项目文档读不到时才退回一句极简兜底（是"指路"，不是纪律副本）。

同时解决"提醒疲劳"：
  v1 每轮注入同一句固定提醒，看到第三轮就麻木了。
  v2 每轮注入的是**项目当前快照**（正在做 / 卡在哪 / 下一步）——内容随项目推进变化，
  有信息量；快照没更新时则明确提示去补（这个提示本身也是在维护 v4 的交接机制）。

设计红线（务必保持）：
  1. 任何异常都必须输出 {"continue": true}，绝不阻断用户提问；
  2. 检测不到框架的项目静默放行，不污染无关工作；
  3. 注入内容保持精简（完整版 ≤ 2000 字符，精简版 ≤ 420 字符）。

自测：
  echo '{"cwd":"D:/000-me-work/top_design","hook_event_name":"SessionStart"}' | python doc-driven-guard.py
  echo '{"cwd":"D:/000-me-work/top_design","hook_event_name":"UserPromptSubmit"}' | python doc-driven-guard.py
"""

import json
import os
import re
import sys

# 识别标志：五文档之一，文件名足够独特，不会误判
DOC_NAME = "00-驱动开发规则.md"
DOC_DIRS = ("开发驱动文档", "docs/开发驱动文档", "文档/开发驱动文档")
ENTRY = "START_HERE.md"
MAX_UP = 6  # 最多向上找 6 层

# 兜底句：仅当读不到项目文档时使用。它只负责"指路"，不复制纪律条款。
FALLBACK = (
    "[文档驱动框架] 本项目已启用文档驱动开发。动手前先读项目根 {entry}，"
    "并加载用户级技能 doc-driven-dev；收尾四步：结论落档 → verify.py 全绿 → "
    "git 提交干净 → 结构变更与「当前快照」同步 START_HERE。"
)

LIMIT_FULL = 2000
LIMIT_LITE = 420
SNAPSHOT_KEYS = ("正在做", "卡在哪", "下一步")


# ---------------------------------------------------------------- 基础工具

def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def clip(s, n):
    """压掉多余空白并限长（用于单行）。"""
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n - 1] + "…"


def clip_total(s, n):
    """多行文本限长（保留换行）。"""
    return s if len(s) <= n else s[:n] + "\n…（已截断，完整规则见 00 文档）"


def strip_md(s):
    return (s or "").replace("**", "").replace("`", "").strip()


# ---------------------------------------------------------------- 定位与提取

def find_root(cwd):
    """从 cwd 向上逐级查找框架根目录，找不到返回 None。"""
    if not cwd:
        return None
    try:
        cur = os.path.abspath(cwd)
    except Exception:
        return None
    for _ in range(MAX_UP):
        for d in DOC_DIRS:
            if os.path.isfile(os.path.join(cur, d, DOC_NAME)):
                return cur
        if os.path.isfile(os.path.join(cur, DOC_NAME)):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None


def locate_rules(root):
    """返回项目里 00 文档的实际路径。"""
    for d in DOC_DIRS:
        p = os.path.join(root, d, DOC_NAME)
        if os.path.isfile(p):
            return p
    p = os.path.join(root, DOC_NAME)
    return p if os.path.isfile(p) else None


def section(text, keyword):
    """按关键词定位二/三级标题所在章节，返回其正文（到下一个同级/更高级标题为止）。
    按关键词而非编号定位 —— 与 verify.py 同思路，抗重编号。"""
    lines = (text or "").splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"^#{2,3}\s", ln) and keyword in ln:
            start = i + 1
            break
    if start is None:
        return ""
    body = []
    for ln in lines[start:]:
        if re.match(r"^#{2,3}\s", ln):
            break
        body.append(ln)
    return "\n".join(body)


def bullets(body, limit=6, width=78):
    """取要点（去 markdown 装饰、限长）。
    兼容三种列表写法：无序 `- ` / `* `，有序 `1. ` / `1) `——
    母版不同章节混用了无序与有序列表，只认一种会漏提取。"""
    out = []
    for ln in (body or "").splitlines():
        s = ln.strip()
        m = re.match(r"^(?:[-*]|\d+[.)])\s+(.*)$", s)
        if not m:
            continue
        t = strip_md(m.group(1))
        if t:
            out.append(clip(t, width))
        if len(out) >= limit:
            break
    return out


def rows(body, limit=6):
    """取表格数据行（自动跳过表头与分隔线）。"""
    out, seen_sep = [], False
    for ln in (body or "").splitlines():
        s = ln.strip()
        if not s.startswith("|"):
            continue
        if set(s) <= set("|-: "):
            seen_sep = True
            continue
        if not seen_sep:
            continue
        cells = [strip_md(c) for c in s.strip("|").split("|")]
        out.append(cells)
        if len(out) >= limit:
            break
    return out


def snapshot(entry_text):
    """从 START_HERE 提取「当前快照」三行。返回 (值字典, 是否已填实)。"""
    vals = {}
    for k in SNAPSHOT_KEYS:
        m = re.search(r"\*\*" + k + r"\*\*[：:]\s*(.*)", entry_text or "")
        vals[k] = (m.group(1).strip() if m else "")
    filled = all(v and "{{" not in v for v in vals.values())
    return vals, filled


# ---------------------------------------------------------------- 两种注入内容

def build_full(root, entry_text, rules_text):
    """SessionStart：从项目文档实时提取纪律要点 + 当前快照。"""
    rp = root.replace("\\", "/")
    p = ["[文档驱动开发框架 · 纪律提醒（钩子实时读项目文档生成，非脚本内嵌副本）]",
         "项目：%s" % rp]

    disc = bullets(section(rules_text, "落档纪律"), limit=5)
    if disc:
        p.append("\n▸ 落档纪律（来自 00 文档）")
        p += ["  %d. %s" % (i, x) for i, x in enumerate(disc, 1)]

    tail_src = section(rules_text, "收尾四步")
    tail = rows(tail_src, limit=5)
    if tail:
        p.append("\n▸ 收尾四步（缺一 = 任务未完成）")
        for r in tail:
            if len(r) >= 2:
                p.append("  %s) %s" % (r[0], clip(r[1], 44)))
    else:
        tb = bullets(tail_src, limit=5)  # 万一被改写成列表也不漏
        if tb:
            p.append("\n▸ 收尾四步（缺一 = 任务未完成）")
            p += ["  %d. %s" % (i, x) for i, x in enumerate(tb, 1)]

    ev = section(rules_text, "证据裁决规则")
    m = re.search(r"^\s*(\S+\s*>\s*\S+.*)$", ev, re.M)
    if m:
        p.append("\n▸ 证据裁决：%s" % clip(m.group(1), 64))

    vals, filled = snapshot(entry_text)
    p.append("\n▸ 项目当前快照（%s）" % ENTRY)
    if filled:
        for k in SNAPSHOT_KEYS:
            p.append("  %s：%s" % (k, clip(vals[k], 56)))
    else:
        p.append("  未更新 —— 请在本轮收尾时补上三行（正在做 / 卡在哪 / 下一步）")

    p.append("\n▸ 入口：先读 %s/%s（四层阅读路径，按需下钻，不要全量读五文档）；"
             "行为层纪律加载技能 doc-driven-dev。" % (rp, ENTRY))
    p.append("  验收：python verify.py（Windows 工作站：E:\\anaconda\\python.exe verify.py）")

    return clip_total("\n".join(p), LIMIT_FULL)


def build_lite(root, entry_text):
    """UserPromptSubmit：注入项目当前快照（动态内容，避免固定复读造成疲劳）。"""
    vals, filled = snapshot(entry_text)
    if filled:
        head = "正在做：%s ｜ 卡在哪：%s ｜ 下一步：%s" % (
            clip(vals["正在做"], 36), clip(vals["卡在哪"], 36), clip(vals["下一步"], 36))
    else:
        head = ("⚠ %s 的「当前快照」未更新（接手者无从判断进度）"
                "—— 本轮收尾请补「正在做 / 卡在哪 / 下一步」三行" % ENTRY)
    tail = "收尾四步：结论落档 → verify.py 全绿 → 提交干净 → 同步 START_HERE（含当前快照）"
    return clip_total("[文档驱动框架] %s ｜ %s" % (head, tail), LIMIT_LITE)


# ---------------------------------------------------------------- 主流程

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw and raw.strip() else {}
    except Exception:
        data = {}

    try:
        event = data.get("hook_event_name") or "UserPromptSubmit"
        cwd = data.get("cwd") or os.environ.get("CODEBUDDY_PROJECT_DIR") or os.getcwd()
        root = find_root(cwd)

        if root is None:
            out = {"continue": True}          # 非文档驱动项目：静默放行
        else:
            entry_path = os.path.join(root, ENTRY).replace("\\", "/")
            entry_text = read_text(os.path.join(root, ENTRY))
            if event == "SessionStart":
                rp = locate_rules(root)
                rules_text = read_text(rp) if rp else ""
                if rules_text:
                    ctx = build_full(root, entry_text, rules_text)
                else:
                    ctx = FALLBACK.format(entry=entry_path)
            else:
                if entry_text:
                    ctx = build_lite(root, entry_text)
                else:
                    ctx = FALLBACK.format(entry=entry_path)
            out = {
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": ctx,
                },
            }
        print(json.dumps(out, ensure_ascii=False))
    except Exception:
        # 兜底：无论如何不阻断用户
        print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
