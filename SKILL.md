---
name: data-factory
description: 多平台数据抓取 AI Skill——从关键词规划到持续数据采集的全生命周期管理
---

# Data-Factory Skill

多平台数据抓取 AI Skill。在用户创建的话题文件夹中，完成从关键词规划、配置生成、数据抓取、关键词发现到调度管理的全流程。

适用于 Cursor、Claude、Claude Code 及其他 AI Agent。

## 安装方式

本 Skill 以 **子模块方式** 放置在用户话题工作目录的 `.claude/data-factory/` 下。

```
<话题目录>/
├── .claude/
│   └── data-factory/       ← 本仓库完整克隆（含 .git）
│       ├── SKILL.md         ← 你正在读的文件
│       ├── modules/
│       ├── knowledge/
│       └── data_factory/    ← Python 包源码
├── config.yaml
├── README.md
├── experiences.md
└── <platform>/              ← 抓取数据
```

**本文件中所有相对路径（`modules/`、`knowledge/`）都是相对于本文件所在目录**，即 `.claude/data-factory/`。
Agent 读取模块文件时需要拼接此前缀路径。

## Phase 0：启动检查

读取本文件后，按顺序执行以下检查：

### 1. 确认 data-factory CLI 可用

```bash
data-factory --help
```

如果命令不存在，提示用户安装：

```bash
cd <data-factory 仓库路径>
pip install -e .
```

### 2. 确认 opencli 可用并激活浏览器桥接

```bash
opencli doctor
```

如果提示浏览器未桥接（Extension 未连接），等待 4 秒后重试，最多重试 3 次：

```
循环最多 3 次：
  1. 执行 opencli doctor
  2. 如果输出包含 [OK] 则通过
  3. 否则等待 4 秒后重试
```

如果 `opencli` 命令不存在，提示用户安装：

```bash
npm install -g @jackwener/opencli
```

### 3. 读取平台知识

读取本文件所在目录下的 `knowledge/platform_quirks.md`，了解各平台已知特性和注意事项。

### 4. 检测项目状态

在用户当前工作目录下查找 `config.yaml`：

- **找到** → 已有项目。读取 `config.yaml` 和 `experiences.md`，根据用户意图路由到对应模块。
- **未找到** → 新项目。进入首次引导流程（读取 `modules/init.md`）。

## 阶段路由

根据项目状态和用户意图，读取并执行对应模块：

| 场景 | 模块 | 说明 |
|------|------|------|
| 工作目录无 `config.yaml` | `modules/init.md` | 首次引导：关键词 → 试搜索 → 配置生成 |
| 用户要抓取/搜索/说"开始抓取" | `modules/fetch.md` | 搜索 + 全量抓取 + 刷新评论 |
| 一轮抓取结束（自动触发） | `modules/discover.md` | 关键词发现与建议 |
| 用户提到定时/调度/自动化 | `modules/schedule.md` | 建议调度计划并管理启停 |
| 抓取出错或用户反馈问题 | `modules/experience.md` | 记录经验、检索已知方案 |

多个模块可串联执行。例如：fetch → discover → 更新 README.md 是一个标准周期。

## 核心规则

以下规则在所有模块中始终生效：

1. **配置确认制**：修改 `config.yaml` 前必须向用户展示变更内容并获得确认
2. **数据不可删除**：不自动删除已抓取的数据，即使数据有问题也只标记不删除
3. **关键词准入制**：新关键词建议必须经用户同意才写入配置
4. **知识先行**：每次启动时读取 `experiences.md` 和 `knowledge/platform_quirks.md`，在操作前检查是否有已知问题
5. **状态同步**：每轮操作结束后自动更新 `README.md` 中的统计信息
6. **错误即经验**：任何失败都应记录到 `experiences.md`，查阅已有经验寻找方案
7. **串行执行**：所有 `data-factory` CLI 命令必须逐条串行执行——等待当前命令完成后再启动下一条，禁止同时运行多个 `data-factory` 进程。`opencli` 依赖单一 Chrome 浏览器实例，并发调用会导致 tab 冲突和任务失败
8. **失败汇总**：每轮抓取结束后，必须输出完整的汇总报告（见 `modules/fetch.md` Step 5 模板）。失败的 URL 必须逐条列出平台、URL、具体失败原因和是否可重试，禁止省略或笼统描述

## CLI 速查表

所有命令均需指定 `--config` 参数指向项目目录下的 `config.yaml`。

### 搜索

```bash
data-factory --config config.yaml search <platform> "<query>" --limit <N>
```

输出：每行一个 URL。

> **注意**：`search` 支持 `--fetch` 参数可搜索后直接抓取，但标准流程**不应使用**此选项。
> 标准流程为 `search` → 去重 → `fetch --from`，确保与已有数据对比后再抓取。

### 抓取

```bash
# 单个 URL
data-factory --config config.yaml fetch "<url>" [--platform <P>] [--force]

# 多个 URL
data-factory --config config.yaml fetch "<url1>" "<url2>" "<url3>"

# 从文件批量抓取
data-factory --config config.yaml fetch --from <urls.txt>

# 从管道读取
echo "<url>" | data-factory --config config.yaml fetch
```

`--force` 忽略已抓取标记，强制重新抓取。
`--platform` 可省略，自动从 URL 识别。
支持同时传入多个 URL 参数和 `--from` 文件，会合并处理。

### 刷新评论

```bash
# 自动判断哪些需要刷新（基于退避策略）
data-factory --config config.yaml refresh

# 强制刷新所有
data-factory --config config.yaml refresh --force

# 刷新单条
data-factory --config config.yaml refresh --platform <P> --id <ID>
```

### 处理

```bash
data-factory --config config.yaml process <transcribe|images> --platform <P> [--id <ID>]
```

### 状态

```bash
# 整体概况
data-factory --config config.yaml status

# 单条详情
data-factory --config config.yaml status --platform <P> --id <ID>
```

### 索引

```bash
data-factory --config config.yaml index rebuild --all
data-factory --config config.yaml index rebuild --platform <P>
data-factory --config config.yaml index status
```

### 导入

```bash
data-factory --config config.yaml import --platform <P> <source_path>
```

### 调度

```bash
data-factory --config config.yaml schedule list
data-factory --config config.yaml schedule start
```

## 给不支持文件读取的 AI

如果你的 AI 工具无法主动读取文件，请将以下文件的内容一并提供给 AI：

1. 本文件 `SKILL.md`
2. 需要的模块文件（`modules/init.md` 或 `modules/fetch.md` 等）
3. `knowledge/platform_quirks.md`
