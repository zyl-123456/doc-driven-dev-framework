## 开发项目治理（常设命令，永久生效，最高优先级）

- **凡是软件开发项目，一律以"文档驱动开发架构"推进**——不做例外。AI 每次接到开发类任务须主动加载用户级技能 `doc-driven-dev`（`~/.workbuddy/skills/doc-driven-dev/`），无需用户提醒。
- 架构三层：**事实层**（项目内五文档 00规则/01需求/02拆解/03方案/04记录 + START_HERE + verify.py）/ **行为层**（上述技能）/ **触发层**（平台钩子，已挂载）。
- **触发层钩子**：`~/.workbuddy/settings.json` 的 `hooks` 字段 → `SessionStart` 注入完整纪律、`UserPromptSubmit` 每轮注入提醒；脚本在 `~/.workbuddy/hooks/doc-driven-guard.py`。判定方式：从工作目录向上找 `开发驱动文档/00-驱动开发规则.md`（或项目根同名文件），命中才注入，非框架项目静默放行。
- 权责铁律：`01` 需求文档为人类主权（AI 受托维护，实质内容须确认）；`02/03/04` 为 AI 全权；`00` 的边界条款改动须人类批准。
- 新项目先跑姐妹技能 `doc-driven-framework-porting`（本地模板 + 移植三步）再进入运行态。
- **模板母版**：`~/.workbuddy/templates/doc-driven-v3/`（本机默认位置；也可放在工作区，母版是唯一权威源）。技能 `doc-driven-framework-porting/templates/` 只是冷启动 copy 用的**发布副本**；母版改动须先经用户验收再同步过去，禁止两边各改各的。
- 编号抽取正则的坑（verify.py 通用化时实测命中）：朴素 `re.findall("Q-\d{3}")` 会抓 `REQ-001` 里的 `Q-001`、`ASM-000` 里的 `M-000` 造成悬空引用误报，必须加负向断言 `(?<![A-Za-z])`。
- 验收命令：`python verify.py`，期望全绿、退出码 0。
