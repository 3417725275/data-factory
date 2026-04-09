---
name: data-factory
description: 多平台数据抓取 AI Skill——从关键词规划到持续数据采集的全生命周期管理
---

# Data-Factory Skill

多平台数据抓取 AI Skill。在用户创建的话题文件夹中，完成从关键词规划、配置生成、数据抓取、关键词发现到调度管理的全流程。

适用于 Cursor、Claude、Claude Code 及其他 AI Agent。

## Phase 0：启动检查

读取本文件后，按顺序执行以下检查：

### 1. 确认工具可用

```bash
data-factory --help
```

如果命令不存在，提示用户安装：

```bash
cd <data-factory 仓库路径>
pip install -e .
```

### 2. 读取平台知识

读取本仓库中的 `knowledge/platform_quirks.md`，了解各平台已知特性和注意事项。

### 3. 检测项目状态

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

## CLI 速查表

所有命令均需指定 `--config` 参数指向项目目录下的 `config.yaml`。

### 搜索

```bash
data-factory --config config.yaml search <platform> "<query>" --limit <N>
```

输出：每行一个 URL。

### 抓取

```bash
# 单个 URL
data-factory --config config.yaml fetch "<url>" [--platform <P>] [--force]

# 从文件批量抓取
data-factory --config config.yaml fetch --from <urls.txt>
```

`--force` 忽略已抓取标记，强制重新抓取。
`--platform` 可省略，自动从 URL 识别。

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
