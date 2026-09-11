# 新设备部署 · 手把手教学

> **这份是给「人」看的**（`README-新设备部署.md` 是给「执行者 / AI」看的）。
> 目标：把老设备上这套「文档驱动开发架构」搬到新设备，并且在新设备上建一个**顶层设计目录（母版工作区）**——
> 以后所有新项目都从它取源，它自己也能持续优化。
> 全程大约 10 分钟，你要动脑子的地方只有三处：**解压**、**发一句话**、**记住一个纪律**。

---

## 零、先打个比方（30 秒看懂原理）

这套架构在电脑上其实是**四样东西，散落在不同角落**，像给一个新员工配的"上岗装备"：

| 装备 | 放在哪 | 什么用 | 打比方 |
|---|---|---|---|
| 技能 `doc-driven-dev` | `~/.workbuddy/skills/` | 干活时的纪律（闭环六步、权限矩阵、收尾四步） | 他**脑子里**的工作手册 |
| 技能 `doc-driven-framework-porting` | 同上 | 一键给新项目建框架 | 他**工具箱里**的开箱工具 |
| 钩子 `doc-driven-guard.py` | `~/.workbuddy/hooks/` | 每次会话/提问**强制**把纪律塞给它 | 墙上那个**到点就响的闹钟** |
| 钩子配置 + 治理记忆 | `~/.workbuddy/settings.json`、`MEMORY.md` | 让闹钟真的通电、让它一进门就知道有这套规矩 | 闹钟的**接线** + 墙上的**岗位职责表** |

**所以为什么不能"拷个文件夹就完事"？** 两个原因：

1. **四样东西不在同一个地方**，得分别摆到位 —— `install.py` 就是那个"装配工"，替你各就各位。
2. **钩子配置里写的是"这台电脑上 Python 的确切位置"**。这就像**门锁配钥匙**：老设备的钥匙配的是老设备的锁，直接拷过去等于拿错钥匙——**锁根本转不动**（钩子静默失效）。所以必须在新设备上**重新配一把**。

另外还有**第五样东西**，就是你要的那个"顶层设计目录"：

> **母版工作区（顶层设计目录）** = 一套**原生态的框架文件**，独立放在一个你能看见、能打开、能改的文件夹里。
> 它不参与"装能力"，而是当**所有新项目的取源母版**。新项目都基于它进一步优化，它自己也会长。

`install.py` 管前面四样（让机器"会"），下面第六节那个脚本管第五样（让框架有个"家"）。

---

## 一、出发前：检查新设备两件事

### ① 装好 WorkBuddy
没有 WorkBuddy，这套东西没地方落脚。先装上、能正常打开。

### ② 有没有 Python（二选一，看你要哪条路线）

钩子和安装脚本都是 Python 程序，**新设备必须有 Python**。两条路线：

| 路线 | 做法 | 优点 | 代价 |
|---|---|---|---|
| **省事** | 什么都不装，让 WorkBuddy 用它**自带的托管 Python** 来装 | 最快，不用额外装东西 | 钩子会绑在 WorkBuddy 自带 Python 上；**将来 WorkBuddy 大版本升级换了 Python，钩子可能失效**，需要再跑一次 `install.py` |
| **稳妥（推荐长期用）** | 新设备自己装一个 Python（Windows 建议装 **E 盘**如 `E:\Python`；macOS 用 `brew install python`） | 钩子绑定稳定路径，不受 WorkBuddy 升级影响 | 多装一个软件 |

> **怎么判断有没有 Python？** 让新设备的 WorkBuddy 帮你查最快——直接问它："本机有哪些 Python？各自的绝对路径是什么？"
> 想自己查：打开终端输 `python3 --version`（Windows 可能是 `python --version`），能打出 `3.8` 以上就行。

### ③ 给文件夹起个"好名字"（别带空格）

你要建的那个顶层设计目录，**建议叫 `top_design`（下划线），别叫 `top design`（空格）**。

原因：带空格的路径在命令行里必须到处加引号，脚本、git、编辑器都可能在这里翻车——**没必要的麻烦**。
（已经建好了带空格的？改名即可，这一步还没开始，改名零成本。）

### ④ 记住你的系统对应写法（跨平台速查）

脚本本身跨平台，只有"路径"和"Python 命令名"随系统不同：

| | Windows | macOS / Linux |
|---|---|---|
| 顶层设计目录 | `D:\top_design` | `~/top_design` |
| Python 命令 | `E:\anaconda\python.exe` | `python3` |
| 终端里切换目录 | `cd /d D:\top_design\deploy-kit` | `cd ~/top_design/deploy-kit` |
| 解压 | 右键「全部解压缩」 | `tar -xzf *.tar.gz` 或 Python（见第四节） |

---

## 二、老设备：拿到压缩包（这步基本不用你动手）

**包已经打好了**，两种格式各一份，随便挑：

```
D:\000-me-work\top_design\dist\doc-driven-kit-v4-20260912.zip        ← 通用
D:\000-me-work\top_design\dist\doc-driven-kit-v4-20260912.tar.gz     ← 含中文文件名时更稳（跨系统推荐）
```

**多大 / 装了什么**（28 个文件，ZIP 约 126 KB / tar.gz 约 98 KB）：

```
deploy-kit/
├── README-新设备部署.md              ← 给执行者/AI 的详细说明书
├── QUICKSTART-新设备手把手教学.md     ← 你正在看的这份
├── install.py                        ← 装配工：装能力层（技能+钩子+配置+记忆）+ 自检
├── init-master-workspace.py          ← 建"顶层设计目录"：把母版铺成一个母版工作区
├── sync-master.py                    ← 同步工具（改了母版后用）
├── package.py                        ← 打包工具（重打包用，同时产出 zip + tar.gz）
└── payload/                          ← 要装的东西都在这儿
    ├── master/        （11 份）母版全套 = 五文档 + README + START_HERE + verify.py + 理解材料三份
    ├── skills/        （9 份）两个技能 + 移植用的 v4 模板七件套
    ├── hooks/         （1 份）触发层钩子 doc-driven-guard.py
    └── memory-section.md（1 份）会追加进新设备用户记忆的治理段
```

> **如果你又改过母版、想重打一个包**：
> ```bash
> cd D:/000-me-work/top_design
> E:/anaconda/python.exe deploy-kit/sync-master.py    # 同步母版 → 技能模板 + 部署包副本
> E:/anaconda/python.exe deploy-kit/package.py        # 重打 dist 里的 zip
> ```
> **顺序别颠倒**：先 `sync-master` 再 `package`，否则包里还是旧内容。

---

## 三、传输：三种方式随便挑

| 方式 | 具体做法 | 适合 |
|---|---|---|
| **U 盘 / 移动硬盘** | 把包拷进去，插到新设备 | 两台电脑在身边 |
| **微信「文件传输助手」** | 老设备发送 → 新设备登录同一微信 → 下载 | 两台电脑不在一起，最省事 |
| **网盘**（百度网盘/腾讯微云等） | 老设备上传 → 新设备下载 | 频繁来回传 |

> 传的是**压缩包**，不是文件夹。压缩包不易丢文件、解压后目录结构原样保留。
>
> ⚠️ **跨系统（Windows ↔ macOS）优先传 `.tar.gz`**：包里的文件名有中文，ZIP 格式对中文名靠"标志位"约定，有些 macOS 自带工具会忽略它、解出 `?????` 乱码。tar 没这问题。包里两种格式都有，随便传哪个都行——**macOS 上用 zip 的话，按第四节的方法解压即可**。

---

## 四、新设备：解压

**Windows**：在包上**右键 → 解压到当前文件夹**（或"全部解压缩"）。

**macOS / Linux**：**别直接用双击 / 自带 `unzip`**（中文名可能变 `?????`）。用下面任一条：

```bash
# 推荐：用 tar.gz
tar -xzf doc-driven-kit-v4-20260912.tar.gz

# 或者用 Python 解 zip（Python 按规范读标志位，绝不出错）
python3 -c "import zipfile; zipfile.ZipFile('doc-driven-kit-v4-20260912.zip').extractall('.')"
```

> **为什么？** 这不是包坏了——包里 15 个中文名条目**都正确带 UTF-8 标志位**（符合 ZIP 规范）。是 **macOS 自带的 `unzip`（老版 Info-ZIP）会忽略这个标志位**，而且它不支持 `-O` 参数。`tar` 或 Python 都能正确处理。

解压到你的顶层设计目录里：
- Windows → `D:\top_design`
- macOS → `~/top_design`

解压完确认里面有 `deploy-kit` 文件夹，进去能看到 `install.py`、`init-master-workspace.py`、`payload`。

> ⚠️ **别在压缩包里直接双击 `install.py`**！必须先把文件解压出来（压缩包内的文件是"只读的临时副本"，跑起来会出错）。

解压后长这样：

```
top_design/                    ← 你的"顶层设计"目录（暂时还只有一个包）
└── deploy-kit/
    ├── install.py
    ├── init-master-workspace.py
    ├── payload/...
    └── ...
```

---

## 五、安装能力层（让新设备"会"这套架构）

### 路线 A · 让 WorkBuddy 自己装（推荐，你基本不用动手）

新设备上打开 WorkBuddy（**Agent 模式**），**把下面这段话原样发给它**（路径按你实际解压的位置改——Windows 形如 `D:\top_design`，macOS 形如 `/Users/你的用户名/top_design`）：

```
我换新设备了，顶层设计目录是 <你的路径>（按实际改）。
请执行两步部署：
① 读取 <你的路径>/deploy-kit/README-新设备部署.md，按说明跑 install.py 装能力层（先 --dry-run 再正式装）；
② 跑 <你的路径>/deploy-kit/init-master-workspace.py --init-git，把这个目录整理成「母版工作区」。
装完必须向我报告：① install.py 的最终 PASS/FAIL 数量；② 钩子脚本在「框架项目」和「非框架项目」下的两种实测输出；
③ ~/.workbuddy/settings.json 的 hooks 字段已写入且原配置未丢；④ 母版 verify.py 自验收结果；
⑤ 告诉我"重启 WorkBuddy + 发一条消息看有没有注入提醒"这条验证怎么做。
```

它会读说明书 → 跑两步 → 把结果报给你。**你不需要懂命令行。**

### 路线 B · 自己动手跑两行命令

```bash
# Windows
cd /d D:\top_design\deploy-kit
python install.py                  # 想看会做什么、先别写盘，就加 --dry-run
python init-master-workspace.py --init-git

# macOS / Linux
cd ~/top_design/deploy-kit
python3 install.py
python3 init-master-workspace.py --init-git
```

用"稳妥路线"那个独立 Python 的话，把 `python` / `python3` 换成它的绝对路径（如 `E:\Python\python.exe install.py`）。

### 跑完你会看到什么

两份逐项报告，结尾分别是：

```
部署结果: 15/15 PASS          ← 能力层装好了
整理结果: 6/6 PASS            ← 母版工作区建好了（git 库内会附带 verify 35/35）
```

**每一项都是"当场跑真脚本验证"出来的**（比如真跑一遍钩子，看在框架项目里注不注入、在非框架项目里静不静默）。看到两个 PASS 就是好了。

> 其它常用参数：`--dry-run`（只看不写）、`--with-codebuddy`（配置路径兜底）、`--target <路径>`（指定母版工作区位置）。
> 重复跑同一条命令**是安全的**：内容一致时会提示"内容一致，跳过"，既不覆盖也不产生备份垃圾。

---

## 六、把目录整理成「顶层设计 / 母版工作区」（你要的那一步）

上一步的 `init-master-workspace.py` 干的就是这件事：**把埋在 `payload/master/` 里的母版"提"到根目录**，让它变成一个真正能用的顶层设计目录。

整理完之后，你的顶层设计目录（Windows 下是 `D:\top_design`，macOS 下是 `~/top_design`）就长这样（**跟老设备的母版完全同构**）：

```
top_design/                      ← 这就是「顶层设计 / 母版工作区」
├── 00-驱动开发规则.md            ┐
├── 01-人类需求描述.md            │
├── 02-需求技术拆解.md            │ 五文档
├── 03-技术实现方案.md            │
├── 04-实现过程记录.md            ┘
├── README.md                     ← 总说明
├── START_HERE.md                 ← 项目入口（模板态）
├── verify.py                     ← 总验收命令
├── 文档导读.md                    ┐
├── 框架评价与边界.md              │ 三份"理解材料"
├── 交接与迭代优化清单.md          ┘
├── hooks/
│   └── doc-driven-guard.py       ← 触发层钩子（权威源）
├── .gitignore
└── deploy-kit/                   ← 部署包原样保留（以后打包/再分发用）
```

**它有什么用？**
- 你能**直接打开、直接看、直接改**——不用去翻那些隐藏目录；
- 它是**唯一权威源**：以后所有新项目都从它取源；
- 它自己**可以被持续优化**（改规则、加条款），改完推给各处副本即可；
- `verify.py` 能在这儿直接跑（建了 git 库就是 **35/35 PASS**；没建是 **34/34**，见下），母版自己也是"被验收"的。

> **关于 34 和 35 这两个数**：`verify.py` 的「git 工作区干净」这一项**只在 git 仓库内才计数**。
> 母版工作区建了 git 库 → 满分 35；`~/.workbuddy/templates/doc-driven-master/`（安装脚本铺的副本）不是 git 仓库 → 满分 34，那一项打印 `[INFO] …跳过`。
> **两个数都算全绿**。所以 `install.py` 报告里的 `34/34` 没少跑东西——别担心。（`init-master-workspace.py --init-git` 会建库，所以你的母版工作区是 35。）

---

## 七、验证：怎么确认它真的在跑（关键一步）

装完**不代表马上生效**——钩子配置需要重启才加载。验证三步：

1. **完全退出 WorkBuddy，重新打开**；
2. 在一个**带框架的项目**里发一条消息（打个"在"都行）；
   - 现在还没有项目？先做第八节，建一个；
3. 看它这一轮的开头，有没有出现这样的提醒：

```
[文档驱动框架] ……
```

- **看见了 → 成了**，后面不用管。
- **没看见 → 多半是配置写错了地方**，在新设备上补跑一次：
  ```bash
  python install.py --with-codebuddy
  ```
  然后重启 WorkBuddy 再试一次。（原因见第十节排错第 ② 条。）

---

## 八、建新设备上的第一个项目（从母版取源）

跟老设备完全一样，**一句话的事**。随便建个空文件夹当项目根，然后在里面开 WorkBuddy 会话，说：

```
给「XX 项目」建文档驱动架构。
```

**它是怎么"从你的顶层设计目录取源"的？**（这个机制值得记一下）

```
顶层设计目录（母版 · 权威源）
      │  sync-master.py 自动推送
      ▼
~/.workbuddy/skills/doc-driven-framework-porting/templates/   （技能的模板 = 母版内容）
      │  建新项目时技能从这里拷贝
      ▼
<你的新项目>/开发驱动文档/   （七件套落地 + 占位符替换 + git 首提交 + verify 全绿）
```

所以你**不需要**每次都手动去母版目录里 cp 文件——只要你改了母版后跑过一次 `sync-master.py`，技能手里的模板就是最新的，建出来的项目自然带最新规则，**不会出现"文档说 A、实际是 B"**。

> ⚠️ **让它把 `verify.py` 顶部的 `MODE` 从 `"template"` 改成 `"project"`**（否则"占位符没清空 / 当前快照没填"不会被抓出来）。**这句话直接跟它说就行**，它知道该怎么做。

---

## 九、日常怎么跟它沟通（照抄话术清单）

| 你想干嘛 | 直接说 |
|---|---|
| 开新项目 | 「给「XX 项目」建文档驱动架构」 |
| 提需求 | 用大白话说"我想要什么效果、我怎么判断好不好"就行，它会转写成 `REQ` 登记 |
| 让它干活 | 「按这个需求往下做」——它会先落档拆解、再写代码记账 |
| 验收 | 「跑一下验收」→ 它执行 `verify.py`，报告全绿还是哪项 FAIL |
| 反馈问题 | 「用起来有个问题：……」→ 它会记进 `01` 反馈区，确认后变成新需求 |
| 中途接手（隔了几天/换了会话） | 「先读 START_HERE，告诉我项目现在在哪」→ 它会读「当前快照」三行再开工 |
| 多任务并行 | 「开两个分支并行做 A 和 B」→ 它会按 `00` 第十三节分配编号段、划定文件主权 |
| **优化母版本身** | 「在顶层设计目录里把 XX 规则加一条」→ 它在母版上改，改完提醒你跑同步 |
| 换新设备 | 「我换新设备了，怎么部署？」→ 见本文件 |

**每一轮结束它都会做完四件事**（缺一件算没干完）：结论落档 → 验收全绿 → 版本提交干净 → 结构变更同步根入口。

---

## 十、排错速查

**① 钩子没生效？**
按顺序查：重启 WorkBuddy → 用 `--with-codebuddy` 重跑 → 确认项目里确实有 `开发驱动文档/00-驱动开发规则.md`。
> **注意**：没有框架的项目里**本来就不该有提醒**（钩子靠这个文件判定，没有就静默放行）——这是正常行为，不是故障。

**② 为什么默认写 `~/.workbuddy/settings.json`，而官方文档说 `~/.codebuddy/settings.json`？**
两套路径并存。**老设备已实测确认 `~/.workbuddy/settings.json` 在 WorkBuddy 桌面版上有效**（挂载后下一轮对话里原样出现了 `[文档驱动框架]` 提醒）。新设备建议先按默认走；万一没生效，`--with-codebuddy` 会**同时**写入 `.codebuddy` 路径兜底。

**③ 新设备没装 Python 也能装吗？**
能。让 WorkBuddy 自己跑安装脚本即可——它用的是 WorkBuddy 手上那个解释器（Windows 上 WorkBuddy 自带托管 Python）。但**长期使用建议换成独立 Python**（见第一节）。

**④ `init-master-workspace.py` 报"目标目录合法"FAIL？**
你把目标指到 `deploy-kit` 里面去了。母版必须铺到它的**上一级**（或别处），否则会把包结构搞乱。默认不填 `--target` 就是上一级，一般不会碰到。

**⑤ `git init` 那步提示提交失败？**
先配一次 git 身份（只需一次）：
```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```
然后重跑 `python init-master-workspace.py --init-git`。

**⑥ 装错了想还原？**
任何被改动的文件都留有 `.bak-<日期>` 备份。删掉新增的 `hooks/`、`skills/doc-driven-*`、`templates/doc-driven-master/` 目录，再把 `.bak` 改回来即可。

**⑦ 会不会干扰新设备上别的项目？**
不会。钩子只认"带框架的项目"，其余目录直接放行、不改变任何行为；它永远不会阻断你——脚本任何异常都只会安静放行。

**⑧ macOS 上解压出来文件名是 `?????` 乱码？**
**不是包坏了**，是 macOS 自带的老版 `unzip` 忽略了 ZIP 的中文名标志位（而且它不支持 `-O` 参数）。改用第四节的办法：
```bash
tar -xzf doc-driven-kit-v4-20260912.tar.gz        # 最省事
# 或
python3 -c "import zipfile; zipfile.ZipFile('doc-driven-kit-v4-20260912.zip').extractall('.')"
```
**根治**：跨系统传含中文名的包，一律优先用 `.tar.gz`（包里两种格式都有）。

**⑨ 钩子将来突然不灵了？**
最常见的原因：走的是"省事路线"（用 WorkBuddy 自带 Python），而 **WorkBuddy 大版本升级换了自带 Python 的路径** → 钩子命令里那个绝对路径不存在了。补跑一次 `python3 install.py` 重新探测路径即可。想一劳永逸就改用独立 Python（见第一节）。

---

## 十一、以后母版改了规则，怎么同步到各处

**在母版工作区里走一条固定流水线**（别手工 cp，容易漏）：

```bash
cd ~/top_design                                     # Windows: cd /d D:\top_design
python3 verify.py                                   # 1. 先确认母版本身全绿（git 库内 35/35，非 git 34/34）
python3 deploy-kit/sync-master.py                   # 2. 母版 → 技能模板 + 部署包副本（加 --check 只看差异）
python3 deploy-kit/package.py                       # 3. 重打 dist 里的包（要分发给别的设备才需要）
```

> **Windows 上把 `python3` 换成 `E:\anaconda\python.exe`（或你装的 Python 绝对路径）。**

第 2 步是最关键的：它会把母版顶到**技能 templates**（这样建新项目用到的就是最新规则），同时刷新部署包里的副本。

> ⚠️ **母版是唯一权威源**。不要拿项目里的副本回头改母版，也不要两台设备各改各的——**那是这套框架唯一的结构性风险点**。
> 要改规则，只改母版工作区，再走上面的流水线推出去。

---

## 附 · 给新设备 WorkBuddy 的照抄指令

嫌第五节那段太长？用这段精简版：

```
读取 <顶层设计目录>/deploy-kit/README-新设备部署.md 和 QUICKSTART-新设备手把手教学.md，
按说明完成两件事：① 跑 install.py 装能力层；② 跑 init-master-workspace.py --init-git 建成母版工作区。
装完把两份报告的结果（PASS/FAIL 数量）和「怎么验证钩子已生效」告诉我。
```

---

## 最后：一句话记住全流程

> **老设备拿包 → 拷到新设备 → 解压到顶层设计目录 → 让 WorkBuddy 跑 `install.py`（装能力）+ `init-master-workspace.py`（建母版）→ 重启 → 建项目时看见 `[文档驱动框架]`，就成了。**
>
> 以后**新项目都从母版取源**；改了母版，跑一次 `sync-master.py`，各处副本自动跟上。
