#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doc-driven-guard.py —— 文档驱动开发框架「防忽略」钩子

挂载位置：WorkBuddy 用户级配置 ~/.workbuddy/settings.json 的 hooks 字段
  事件一：SessionStart    —— 新会话开始，注入完整纪律
  事件二：UserPromptSubmit —— 每次提问，注入一行极简提醒

它解决什么问题：
  框架文件躺在项目里，AI 不主动读就等于不存在。本钩子由平台在每次会话/提问时
  强制调用，把框架纪律直接塞进 AI 的输入上下文，绕不过去。

设计红线（务必保持）：
  1. 任何异常都必须输出 {"continue": true}，绝不阻断用户提问；
  2. 检测不到框架的项目静默放行，不污染无关工作；
  3. 注入内容保持精简，不白占上下文。

自测：
  echo '{"cwd":"D:/000-me-work/top_design","hook_event_name":"UserPromptSubmit"}' | python doc-driven-guard.py
"""

import json
import os
import sys

# 识别标志：五文档之一，文件名足够独特，不会误判
DOC_NAME = "00-驱动开发规则.md"
DOC_DIRS = ("开发驱动文档", "docs/开发驱动文档", "文档/开发驱动文档")
ENTRY = "START_HERE.md"
MAX_UP = 6  # 最多向上找 6 层

LITE = (
    "[文档驱动框架] 本项目已启用文档驱动开发。动手前先读项目根 {entry}，"
    "并加载用户级技能 doc-driven-dev；收尾按四步走：结论落档 → verify.py 全绿 → git 提交干净 → 结构变更同步 START_HERE。"
)

FULL = """[文档驱动开发框架 · 纪律提醒（由钩子强制注入，请勿忽略）]
当前项目 {root} 已建立文档驱动框架，本轮工作必须按下列纪律推进：

1. 入口：先读项目根 {entry}（四层阅读路径），按「我想…」表定位要看的文档，**不要全量读五文档**。
2. 行为层：加载用户级技能 doc-driven-dev —— 闭环六步、文档权限矩阵、收尾四步、即时对齐审计。
3. 权责：`01-人类需求描述.md` 为人类主权（实质内容须确认后再写），`02/03/04` 由 AI 全权维护。
4. 收尾四步（缺一项即视为任务未完成）：关键结论落档 → `verify.py` 全绿 → git 工作区干净 → 目录/模块/状态有变动则同轮同步 `START_HERE.md`。
5. 验收命令：{verify}
"""


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
            # 非文档驱动项目：静默放行
            out = {"continue": True}
        else:
            entry = os.path.join(root, ENTRY).replace("\\", "/")
            if event == "SessionStart":
                ctx = FULL.format(root=root.replace("\\", "/"), entry=entry,
                                  verify="python verify.py（Windows 工作站：E:\\anaconda\\python.exe verify.py）")
            else:
                ctx = LITE.format(entry=entry)
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
