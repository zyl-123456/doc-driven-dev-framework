# 文档驱动开发框架

当前版本 **5.0.1**（2026-10-10）。五份文档保存人类意图、重要设计与证据，帮助 AI 按需获取项目背景。简单修改直接实现并检查，复杂功能再拆解；不要求每轮填表、验收或提交。

## 母版与使用入口

本仓库是模板母版；00–04 和 START_HERE 中的占位符是正常留白。产品项目复制后按实际填写或删除不适用项。

| 需要做什么 | 入口 |
|---|---|
| 看 v4 → v5 的理由、差异和迁移 | [v5 发布说明](releases/v5.0.1.md) |
| 看所有正式版本 | [CHANGELOG](CHANGELOG.md) |
| 理解五份文档 | [文档导读](文档导读.md) |
| 理解收益、代价与证据边界 | [框架评价与边界](框架评价与边界.md) |
| 把框架放进新项目 | [移植技能](skills/doc-driven-framework-porting/SKILL.md) |
| AI 日常如何使用 | [运行技能](skills/doc-driven-dev/SKILL.md) |
| 换设备部署 WorkBuddy 适配器 | [部署说明](deploy-kit/README-新设备部署.md) |
| 维护、提交与发布版本 | [贡献与版本管理](CONTRIBUTING.md) |
| 后续效果评估 | [优化清单](交接与迭代优化清单.md) |

## 新项目开始

复制 00–04 到项目的 `开发驱动文档/`，START_HERE 和 verify.py 放项目根。填写目标、约束、已有授权与初始验收样例；技术事项不需要时写“不需要独立拆解”。把 START_HERE 的任务入口换成实际相对链接。

`python verify.py` 自动识别母版与项目；也可明确用 `--mode project`。不再要求改脚本开关。检查通过仅证明结构与显式引用，功能测试和人工验收写在 03。

Codex 等工具可用自己的项目指令入口，只需指向 START_HERE 与相关约束。WorkBuddy 钩子是可选适配器，不能当作所有工具通用机制。无需钩子也可使用本框架。

## 仓库内的权威来源

- 00–04、START_HERE、verify.py：产品模板。
- `skills/`：技能正文权威来源。
- `hooks/`：可选 WorkBuddy 钩子权威来源。
- `deploy-kit/payload/`：生成的发布副本，不手改，不从机器旧技能反向覆盖。
- VERSION、CHANGELOG、releases：版本、理由和迁移记录。
- tests、GitHub Actions：脚本行为回归与自动检查。
- _archive、.workbuddy/memory：历史材料，默认不加载；历史陈述不等于当前规则或授权。

## 验证与发布

```text
python deploy-kit/sync-master.py
python -m unittest discover -s tests -v
python verify.py
```

日常允许工作区有未提交改动。正式发布前提交，再运行 `python verify.py --release`，然后打包、建立标签和 GitHub Release。每个正式版本必须说明问题、改动原因、前后差异、验证与限制；具体流程见 CONTRIBUTING。

## 已确认与未验证

当前版本提供结构检查、显式编号与链接检查、规模提醒、技能和部署工具。减少上下文重复与流程负担是设计目标；没有完成模型任务对照实验，不宣称已证明 token 节省比例或开发成功率提升。

历史版本通过 Git 标签和发布说明查阅，不覆写旧历史。v4 的母版基线是 `16e6c71`。
