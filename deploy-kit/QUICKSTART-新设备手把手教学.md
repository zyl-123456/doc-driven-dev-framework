# 新设备快速开始 · v5

你有两种实际需要：只想让 AI 使用五份文档，复制模板并告诉它从 START_HERE 开始即可；需要 WorkBuddy 自动显示短入口，再安装可选适配器。

## 安装适配器

从 GitHub Release 下载当前版本压缩包和 SHA-256 清单，核对哈希后解压。告诉新设备的 AI：

> 读取这个包的 deploy-kit/README-新设备部署.md，先检查安装计划，再在我的授权范围内安装。保留原有配置与记忆，报告脚本验证结果和仍需我在客户端验证的事项。

需要手动运行时，进入解压后的 deploy-kit：
```text
python install.py --dry-run
python install.py
python init-master-workspace.py --target <母版目录>
```
macOS / Linux 上通常使用 python3。母版目录可以包含空格，命令中给路径加引号。

## 怎么知道成功

安装脚本报告 PASS 说明发布清单、脚本行为和文件部署检查通过。重启 WorkBuddy，在一个框架项目中新建会话，核对短入口是否进入上下文，才算确认当前客户端触发。普通消息不再逐轮注入收尾提醒。

## 旧版本升级

原项目内容保留，只迁移已授权的规则和检查器；别拿模板覆盖人类需求。旧全局治理记忆由人类决定如何更新，安装器不会自动修改。每版变化与理由在 CHANGELOG 和 releases 里查。

## 母版日常使用

修改母版源 → 同步仓库内副本 → 测试 → 记录正式版本 → 提交 → 发布检查 → 打包与 GitHub Release。同步不会偷偷改 WorkBuddy 配置；需要升级安装时单独执行 install.py。
