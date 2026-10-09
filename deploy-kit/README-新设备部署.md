# 可选 WorkBuddy 部署 · v5.0.1

本工具安装技能和短入口钩子，不是使用五文档的前提，也不是 Codex 的配置方式。其他 AI 工具使用自己的项目指令入口即可。

## 安装

需要 Python 3.9+。从 GitHub Release 下载 ZIP 或 tar.gz 及 SHA-256 清单，核对文件哈希并解压。中文路径兼容性有问题时用 Python zipfile 解压或改用 tar.gz。

在 deploy-kit 目录运行：

```text
python install.py --dry-run
python install.py
python init-master-workspace.py --target <你的母版目录>
```

可加 --init-git 建立版本库；Git 身份未配置时报告失败并保留文件。默认母版目标为 deploy-kit 上一级。第一次安装后重启客户端，在真实框架项目中验证 SessionStart 注入；不能用脚本自测替代。

## 安装边界

安装器先核对发布清单和钩子行为，再处理配置。保留无关 hooks、配置与用户记忆；仅替换本适配器的旧路径和挂载，并移除本适配器的 UserPromptSubmit 提醒。只在 SessionStart 注入短入口。重复安装相同内容不创建新备份；变更前备份对应文件。

默认写 .workbuddy/settings.json；--with-codebuddy 可增加 .codebuddy 配置。若该处已有本适配器旧挂载，也会更新，避免旧提醒残留。平台是否支持这些配置需要真实客户端确认。

v5 不自动写入全局治理记忆。已有“一律使用、最高优先级”等 v4 记忆须在授权内单独核对；本安装器只提示，不修改。

## 母版与副本

母版包含模板、skills、hooks、版本记录和回归测试。改动后运行：
```text
python deploy-kit/sync-master.py
python deploy-kit/sync-master.py --check
```

同步只处理仓库内副本，差异或未知副本返回非零，不读写本机已安装技能。若需要让 WorkBuddy 采用新技能，明确执行 install.py；不会因同步母版自动改客户端配置。

## 发版

日常检查与正式发布检查不同。正式版本的提交、标签、发布说明和 GitHub Release 操作见母版 CONTRIBUTING.md。复制已有产品时不能用空模板覆盖需求和证据。
