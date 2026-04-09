# Data-Factory AI Skill 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 data-factory 仓库中创建平台无关的 AI Skill 文档体系（SKILL.md + 5 个模块 + 2 个知识文件），使任何 AI Agent 能通过读取 SKILL.md 来驱动多平台数据抓取的全生命周期。

**Architecture:** 主入口 `SKILL.md` 负责前置检查和阶段路由，具体操作流程拆分到 `modules/` 下的独立文档。`knowledge/` 存放跨项目共享的平台知识和经验模板。Agent 通过调用 `data-factory` CLI 完成实际数据操作，不需要修改现有源码。

**Tech Stack:** Markdown 文档，`data-factory` CLI（Python），YAML 配置

---

## 文件结构

| 文件 | 职责 |
|------|------|
| Create: `knowledge/platform_quirks.md` | 跨项目共享的平台经验知识库 |
| Create: `knowledge/experiences_template.md` | 经验记录格式模板 |
| Create: `SKILL.md` | Skill 入口：前置检查、阶段路由、核心规则、CLI 速查 |
| Create: `modules/init.md` | 首次引导流程：话题 → 关键词 → 试搜索 → 配置生成 |
| Create: `modules/fetch.md` | 搜索与抓取操作流程 |
| Create: `modules/discover.md` | 关键词发现与建议 |
| Create: `modules/experience.md` | 经验记录、检索与提炼 |
| Create: `modules/schedule.md` | 调度建议与管理 |

无需修改现有源码。`config.yaml` 中新增的 `project` 段由 Agent 直接读写 YAML，`data-factory` CLI 会自动忽略未知字段。

---

### Task 1: 知识库基础文件

**Files:**
- Create: `knowledge/platform_quirks.md`
- Create: `knowledge/experiences_template.md`

- [ ] **Step 1: 创建 `knowledge/platform_quirks.md`**

```markdown
# 平台经验知识库

> 本文件由 data-factory Skill 维护，记录跨项目通用的平台特性和已知问题。
> Agent 每次启动时读取本文件，避免重复踩坑。
> 当同一问题在项目级 `experiences.md` 中出现 ≥ 3 次时，应提炼到本文件。

## YouTube

- `opencli youtube search` 返回的 URL 格式为 `https://www.youtube.com/watch?v=<id>`
- 评论抓取在高峰期（UTC 14:00-20:00）可能超时，建议 rate_limit ≥ 2.0
- 部分视频禁用了评论，`fetch_comments` 会返回空列表而非报错

## Bilibili

- `opencli bilibili search` 返回的 URL 格式为 `https://www.bilibili.com/video/<BVid>`
- B站有反爬机制，建议 rate_limit ≥ 1.0，连续抓取超过 50 条可能触发验证码
- 部分视频需要登录才能查看完整评论

## Reddit

- `opencli reddit search` 返回的 URL 格式为 `https://www.reddit.com/r/<sub>/comments/<id>/...`
- Reddit API 对未认证请求有严格限流，建议 rate_limit ≥ 2.0
- 评论树结构较深，抓取时间可能较长

## 小红书

- `opencli xiaohongshu` 依赖特定 cookie 或登录态，可能需要定期更新
- 图片 URL 有防盗链，下载时需要带 referer header

## 知乎

- `opencli zhihu` 搜索结果混合了问题和文章
- 评论功能尚未在 opencli 中实现（待定）

## Twitter/X

- `opencli twitter` 需要有效的 API 凭证
- rate_limit 建议 ≥ 2.0，Twitter API 限制较严

## TikTok

- 视频下载依赖 `yt-dlp`，需确保已安装
- 评论功能尚未在 opencli 中实现（待定）

## Discourse

- 使用 REST API 直接访问，需要配置 `base_url`
- 不同 Discourse 实例的 API 版本可能不同，注意兼容性
- 搜索结果分页默认 50 条

## GitHub

- 使用 REST API，未认证时限速 60 次/小时，配置 token 后 5000 次/小时
- Issue 和 PR 的评论是分开的 API 端点
- 搜索 API 有独立限速（每分钟 30 次）
```

- [ ] **Step 2: 创建 `knowledge/experiences_template.md`**

```markdown
# 经验记录模板

> 本文件定义项目级 `experiences.md` 的记录格式。
> Agent 初始化项目时，将此模板的格式说明头复制到项目的 `experiences.md` 中。

## 格式说明

每条经验记录使用以下模板，追加到 `experiences.md` 末尾：

### YYYY-MM-DD HH:MM

- **平台**: <platform name>
- **操作**: <具体操作，如 fetch / search / fetch_comments / process>
- **现象**: <发生了什么>
- **解决**: <如何解决的，如果未解决则写"待解决">
- **教训**: <从中学到了什么>
- **可复用**: 是/否
- **自动应用**: <Agent 后续遇到相同情况时的自动处理规则，如果不适用则留空>

## 示例

### 2026-04-08 14:30

- **平台**: YouTube
- **操作**: fetch_comments
- **现象**: 连续 3 个视频评论抓取超时（timeout 30s）
- **解决**: 将 config.yaml 中 YouTube 的 rate_limit 从 2.0 调整为 3.5 后恢复
- **教训**: YouTube 评论 API 在北京时间晚间高峰期需要更大请求间隔
- **可复用**: 是
- **自动应用**: 检测到 YouTube 连续超时 ≥ 2 次时，建议用户将 rate_limit 调大 50%

## 提炼规则

当同一平台 + 同一类问题出现 ≥ 3 次时，Agent 应提示将经验提炼到仓库级
`knowledge/platform_quirks.md` 中，使所有项目受益。
```

- [ ] **Step 3: 提交**

```bash
git add knowledge/platform_quirks.md knowledge/experiences_template.md
git commit -m "docs: add platform quirks knowledge base and experience template"
```

---

### Task 2: SKILL.md 入口文件

**Files:**
- Create: `SKILL.md`

- [ ] **Step 1: 创建 `SKILL.md`**

```markdown
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
```

- [ ] **Step 2: 提交**

```bash
git add SKILL.md
git commit -m "docs: add SKILL.md entry point for AI Skill"
```

---

### Task 3: 首次引导模块

**Files:**
- Create: `modules/init.md`

- [ ] **Step 1: 创建 `modules/init.md`**

```markdown
# 首次引导流程

> 当用户工作目录下不存在 `config.yaml` 时执行本流程。
> 目标：从零开始，引导用户完成话题定义、关键词梳理、平台选择、配置生成。

## Step 1：了解话题

询问用户：

1. 想研究/抓取什么话题？
2. 研究目的是什么？（跟踪行业动态 / 深度分析 / 素材收集 / 竞品监控...）
3. 有没有特定的范围限制？（时间范围、语言偏好、特定社区等）

记住用户的回答，用于后续步骤。

## Step 2：梳理关键词

基于用户描述的话题，头脑风暴一批候选关键词（中英文混合）。

**展示格式：**

```
根据「<话题>」，建议以下关键词：

核心词：
- <keyword1>、<keyword2>、<keyword3>

扩展词：
- <keyword4>、<keyword5>、<keyword6>

英文对应：
- <keyword7>、<keyword8>、<keyword9>

你要保留哪些？有想补充的吗？
```

用户确认后确定关键词列表。关键词为简单数组，不区分语言。

## Step 3：选择平台

展示所有可用平台，根据话题属性给出建议：

```
可用平台：
  ✅ 建议启用：YouTube、Bilibili、Reddit、GitHub、Twitter
  ⚡ 可选启用：知乎、小红书、TikTok、Discourse

建议理由：<根据话题特性说明>

要启用哪些？
```

**平台选择参考：**

| 话题类型 | 推荐平台 |
|---------|---------|
| 技术/编程 | YouTube, Bilibili, Reddit, GitHub, Twitter |
| 学术/研究 | YouTube, Reddit, GitHub, 知乎, Discourse |
| 消费/生活 | 小红书, Bilibili, TikTok, Twitter |
| 新闻/时事 | Twitter, Reddit, YouTube |

如果启用 Discourse，需要询问 Discourse 实例的 URL。
如果启用 GitHub，询问是否有 Personal Access Token（可选，提高限速）。

## Step 4：试搜索验证

用确定的关键词在各平台执行小范围搜索：

```bash
data-factory --config config.yaml search <platform> "<keyword>" --limit 3
```

> 注意：此时 config.yaml 尚未生成。Agent 需要先创建一个临时的最小化 config.yaml
> （仅包含 `output_dir` 和 `platforms` 部分），用于执行试搜索。
> 试搜索完成后，临时配置会被完整配置覆盖。

**临时配置模板：**

```yaml
output_dir: "."
platforms:
  <platform>:
    enabled: true
    rate_limit: 2.0
network:
  proxy: ""
  timeout: 30
  retry: 3
```

**展示结果摘要：**

```
试搜索结果：

YouTube "AI agent" → 3 条：
  1. <title> - <views>
  2. <title> - <views>
  3. <title> - <views>

Reddit "AI agent" → 3 条：
  1. <subreddit> - <title>
  2. ...

方向对吗？要调整关键词吗？
```

如果用户要调整，回到 Step 2。

## Step 5：生成配置

生成三个文件：

### config.yaml

```yaml
project:
  name: "<话题名>"
  description: "<用户描述的研究目的>"
  keywords: [<确认后的关键词列表>]
  created_at: "<ISO 8601 时间戳>"

output_dir: "."
log_level: "info"

transcribe:
  whisper_api:
    enabled: false
    api_key: ""
    model: "whisper-1"
    base_url: "https://api.openai.com/v1"
  whisper_local:
    enabled: false
    model_size: "large-v3"
    device: "cuda"
  platform_subtitle:
    enabled: true

platforms:
  # 根据 Step 3 用户确认的平台生成，未启用的平台 enabled: false
  youtube:
    enabled: true
    rate_limit: 2.0
  bilibili:
    enabled: true
    rate_limit: 1.0
  # ... 其他平台

scheduler:
  enabled: false
  jobs: []

network:
  proxy: ""
  timeout: 30
  retry: 3
```

询问用户：
- 是否需要配置代理？（填入 `network.proxy`）
- 是否有 OpenAI API Key 用于视频转录？（填入 `transcribe.whisper_api`）
- 是否有 GitHub Token？（填入 `platforms.github.token`）

### README.md

```markdown
# <话题名>

<用户描述的研究目的>

## 关键词

<关键词列表，逗号分隔>

## 启用平台

| 平台 | 状态 | 数据量 | 最后抓取 |
|------|------|--------|---------|
| <platform> | ✅ 启用 | 0 条 | - |
| ... | ... | ... | ... |

## 目录结构

- `config.yaml` — 项目配置（关键词、平台、调度等）
- `experiences.md` — 操作经验日志
- `<platform>/` — 各平台抓取数据，每条记录一个子文件夹
- `<platform>/index.json` — 平台索引
- `global_index.json` — 全局汇总索引

## 数据格式

每条抓取记录存储为一个文件夹，包含：
- `meta.json` — 元数据（标题、URL、抓取时间、评论刷新状态等）
- 内容文件（`description.txt` / `content.md` / `comments.json` 等）
- `assets/` — 媒体文件（缩略图、图片等）
```

### experiences.md

从 `knowledge/experiences_template.md` 复制格式说明头，创建空的经验日志文件：

```markdown
# 操作经验日志

> 本文件记录项目操作过程中的经验和教训。
> Agent 每次启动时读取本文件，遇到类似问题时参考已有方案。
> 格式参考 data-factory 仓库中的 `knowledge/experiences_template.md`。

---

```

将生成的配置展示给用户确认后再写入文件。

## Step 6：建议调度计划

读取 `modules/schedule.md` 中的建议策略，根据启用的平台和关键词数量生成建议：

```
建议调度计划：
- YouTube/Bilibili: 每天 08:00 搜索，每个关键词 limit 10
- Reddit/Twitter: 每天 12:00 搜索
- GitHub: 每 3 天 08:00 搜索
- 评论刷新: 每天 02:00
- 小红书/知乎: 每天 20:00 搜索

要调整吗？确认后写入配置。
```

用户确认后更新 `config.yaml` 的 `scheduler` 段：

```yaml
scheduler:
  enabled: true
  jobs:
    - name: "daily_youtube"
      platform: "youtube"
      action: "search"
      query: "<keyword>"
      cron: "0 8 * * *"
      limit: 10
    # ... 其他平台
```

## Step 7：首轮抓取

```
配置完成！要现在执行首轮抓取吗？
```

如果用户同意，读取 `modules/fetch.md` 执行抓取流程。
```

- [ ] **Step 2: 提交**

```bash
git add modules/init.md
git commit -m "docs: add init module for first-time project setup"
```

---

### Task 4: 抓取操作模块

**Files:**
- Create: `modules/fetch.md`

- [ ] **Step 1: 创建 `modules/fetch.md`**

```markdown
# 搜索与抓取操作

> 执行日常的搜索、抓取、评论刷新工作。
> 触发场景：用户主动要求 / 首次引导后的首轮抓取 / 调度任务触发。

## Step 1：加载上下文

1. 读取 `config.yaml`，获取 `project.keywords` 和启用的平台列表
2. 读取 `experiences.md`，了解本项目的历史问题
3. 读取 `knowledge/platform_quirks.md`（如果尚未在 Phase 0 读取）

## Step 2：搜索并全量抓取

### 2.1 搜索

遍历每个启用的平台，对每个关键词执行搜索：

```bash
data-factory --config config.yaml search <platform> "<keyword>" --limit <N>
```

`search` 命令输出每行一个 URL。收集所有 URL。

### 2.2 去重

读取 `global_index.json`（如存在），将搜索到的 URL 与已有记录对比，过滤掉已抓取的 URL。

如果 `global_index.json` 不存在，先执行：

```bash
data-factory --config config.yaml index rebuild --all
```

### 2.3 全量抓取

将去重后的新 URL 写入临时文件（如 `.fetch_urls.tmp`），然后执行：

```bash
data-factory --config config.yaml fetch --from .fetch_urls.tmp
```

抓取完成后删除临时文件。

在内存中记录本轮抓取的 URL 列表，供关键词发现阶段使用。

**不暂停等待用户确认**，除非用户主动中断。

## Step 3：错误处理

监控抓取命令输出中的 `ERROR` 行。对于失败的 URL：

1. **记录经验**：按 `knowledge/experiences_template.md` 格式追加到 `experiences.md`
2. **检索方案**：
   - 搜索 `experiences.md` 中是否有同平台 + 同类错误的记录
   - 搜索 `knowledge/platform_quirks.md` 中是否有相关说明
3. **自动重试**（如果有可应用的方案）：
   - 超时类错误 → 建议用户调大 rate_limit，重试
   - 网络类错误 → 检查代理设置，重试
   - 其他错误 → 跳过，在汇总中标记
4. **跳过**（如果无方案）：记录到最终汇总中

## Step 4：刷新评论

```bash
data-factory --config config.yaml refresh
```

此命令自动按退避策略判断哪些条目需要刷新。

## Step 5：抓取后汇总

输出汇总报告：

```
本轮抓取完成：

📊 搜索结果
- 搜索关键词: <N> 个 × <M> 个平台
- 发现 URL: <total> 条（去重后新增 <new> 条）

📥 抓取结果
- 成功: <N> 条（YouTube <n1>, Reddit <n2>, ...）
- 失败: <N> 条（原因汇总）
- 跳过: <N> 条（已存在）

💬 评论刷新
- 已刷新: <N> 条
- 未到期: <N> 条

🔄 后处理
- 转录完成: <N> 条
- 图片下载: <N> 条
```

### 后续自动操作

1. 执行 `modules/discover.md` 的关键词发现流程
2. 更新 `README.md` 中的统计信息（读取 `global_index.json` 或 `data-factory status` 输出）
3. 重建索引（如有新数据）：

```bash
data-factory --config config.yaml index rebuild --all
```

## 更新 README.md

读取 `data-factory --config config.yaml status` 的输出，更新 `README.md` 中的平台状态表：

```markdown
## 启用平台

| 平台 | 状态 | 数据量 | 最后抓取 |
|------|------|--------|---------|
| youtube | ✅ 启用 | 127 条 | 2026-04-09 |
| reddit | ✅ 启用 | 45 条 | 2026-04-09 |
| ... | ... | ... | ... |

**总计**: 200 条数据，最后更新: 2026-04-09 16:30
```

同时更新关键词列表（如在 discover 阶段有变更）。
```

- [ ] **Step 2: 提交**

```bash
git add modules/fetch.md
git commit -m "docs: add fetch module for search and scraping operations"
```

---

### Task 5: 关键词发现模块

**Files:**
- Create: `modules/discover.md`

- [ ] **Step 1: 创建 `modules/discover.md`**

```markdown
# 关键词发现与建议

> 每轮抓取结束后自动触发。也可由用户主动要求执行。
> 目标：从已抓取内容中发现有价值的新关键词，建议给用户。

## 前置条件

- 本轮至少新增 5 条内容，否则跳过发现流程并提示"数据量不足，暂不建议新关键词"
- 已在内存中记录本轮抓取的 URL 列表（由 `modules/fetch.md` 传递）

## Step 1：文本频率分析

读取本轮新抓取内容的以下字段：

- 各 `meta.json` 中的 `title`
- 各 `meta.json` 中 `platform_meta` 下的标签类字段（`tags`、`flair`、`topics` 等）
- `description.txt` / `content.md` 的正文（如有）

提取高频出现的词汇或短语，排除：
- 当前 `config.yaml` 的 `project.keywords` 中已有的词
- 常见停用词（的、了、the、a、is 等）
- 平台名和通用词汇

## Step 2：LLM 语义分析

Agent 自身即为 LLM，直接对以下内容进行分析（不需要调用外部 API）：

**输入：**
- 本轮抓取的标题列表
- Step 1 提取的高频词
- 当前关键词列表

**分析目标：**
- 有哪些值得追踪的相关子话题？
- 有没有新出现的术语、项目名、工具名？
- 当前关键词中是否有冗余（搜索结果高度重叠）？
- 当前关键词是否有覆盖不足的方向？

## Step 3：汇总建议

合并 Step 1 和 Step 2 的结果，去重后以一条消息呈现：

```
关键词发现建议：

🆕 高频新词（出现 5+ 次）：
- <word1>、<word2>、<word3>

🔍 相关子话题：
- <topic1>: <简要说明为什么值得关注>
- <topic2>: <简要说明>

⚠️ 冗余提示：
- "<keyword_a>" 和 "<keyword_b>" 搜索结果高度重叠，可考虑合并

要加入哪些？直接告诉我。
```

## 约束

- 每轮最多建议 10 个新关键词，避免信息过载
- 只有用户明确同意的关键词才写入配置
- 写入操作：更新 `config.yaml` 的 `project.keywords` 数组，需向用户确认变更内容
- 写入后同步更新 `README.md` 中的关键词列表
```

- [ ] **Step 2: 提交**

```bash
git add modules/discover.md
git commit -m "docs: add discover module for keyword suggestion"
```

---

### Task 6: 经验管理模块

**Files:**
- Create: `modules/experience.md`

- [ ] **Step 1: 创建 `modules/experience.md`**

```markdown
# 经验记录与检索

> 管理两层知识体系：项目级 `experiences.md` 和仓库级 `knowledge/platform_quirks.md`。
> 触发场景：抓取出错 / 用户反馈问题 / Agent 主动记录。

## 两层知识体系

| 层级 | 文件 | 位置 | 作用域 |
|------|------|------|--------|
| 项目级 | `experiences.md` | 当前话题工作目录 | 单个项目 |
| 仓库级 | `knowledge/platform_quirks.md` | data-factory 仓库 | 所有项目共享 |

## 何时记录

以下情况必须记录到项目级 `experiences.md`：

1. **抓取失败或超时** — 记录平台、错误信息、解决方案
2. **平台行为变化** — API 返回格式变化、新的限制
3. **用户纠正** — 用户指出 Agent 操作不当
4. **异常缓慢** — 某个操作耗时远超预期
5. **重试成功** — 记录什么方案解决了问题

## 记录格式

严格按照 `knowledge/experiences_template.md` 中定义的格式：

```markdown
### YYYY-MM-DD HH:MM

- **平台**: <platform>
- **操作**: <fetch / search / fetch_comments / process / ...>
- **现象**: <具体发生了什么>
- **解决**: <如何解决的，未解决写"待解决">
- **教训**: <从中学到了什么>
- **可复用**: 是/否
- **自动应用**: <后续遇到时的自动处理规则>
```

追加到 `experiences.md` 文件末尾。

## 检索经验

遇到问题时，按以下顺序检索：

1. 在 `experiences.md` 中搜索同平台 + 同类操作的记录
2. 在 `knowledge/platform_quirks.md` 中搜索对应平台的段落
3. 如果找到匹配的「自动应用」规则，直接执行（或建议用户执行）
4. 如果找到相关但不完全匹配的记录，参考其解决方案

## 自动提炼

### 触发条件

当同一平台 + 同一类问题在 `experiences.md` 中出现 **≥ 3 次** 时触发。

### 提炼流程

1. Agent 提示用户：

```
这个问题已经出现 3 次了：<问题摘要>

建议提炼到 knowledge/platform_quirks.md，所有项目都能受益。
要提炼吗？
```

2. 用户确认后，Agent 将经验浓缩为一条简明规则，追加到 `knowledge/platform_quirks.md` 对应平台的段落下。

3. 在原始 `experiences.md` 的相关记录旁标注「已提炼」。

### 提炼格式

在 `knowledge/platform_quirks.md` 中追加：

```markdown
- <简明的经验描述>（来源：<项目名> experiences.md，<日期>）
```
```

- [ ] **Step 2: 提交**

```bash
git add modules/experience.md
git commit -m "docs: add experience module for knowledge management"
```

---

### Task 7: 调度管理模块

**Files:**
- Create: `modules/schedule.md`

- [ ] **Step 1: 创建 `modules/schedule.md`**

```markdown
# 调度建议与管理

> 管理定时抓取任务：建议调度计划、配置写入、启停控制、自适应调整。
> 触发场景：首次引导 Step 6 / 用户主动要求 / Agent 发现长时间未抓取。

## 建议策略

### 依据因素

| 因素 | 影响 |
|------|------|
| 关键词数量 | 多 → 降低单次 limit 或分批执行 |
| 平台特性 | 实时性强频率高，慢变频率低 |
| rate_limit | 间隔大的平台不宜高频 |
| 历史经验 | 频繁超时 → 降低频率或换时段 |

### 默认建议模板

| 平台 | 频率 | 默认时间 | 说明 |
|------|------|---------|------|
| YouTube | 每天 1 次 | 08:00 | 视频更新适中 |
| Bilibili | 每天 1 次 | 08:00 | 同上 |
| Reddit | 每天 1 次 | 12:00 | 讨论更新较快 |
| Twitter | 每天 1 次 | 12:00 | 实时性强 |
| GitHub | 每 3 天 1 次 | 08:00 | 仓库/Issue 变化慢 |
| Discourse | 每 2 天 1 次 | 10:00 | 论坛更新适中 |
| 小红书 | 每天 1 次 | 20:00 | 晚间更新多 |
| 知乎 | 每天 1 次 | 20:00 | 同上 |
| TikTok | 每天 1 次 | 20:00 | 同上 |
| 评论刷新 | 每天 1 次 | 02:00 | 低峰期执行 |

### 关键词数量对 limit 的影响

| 关键词数 | 每个搜索的 limit |
|---------|-----------------|
| 1-3 | 20 |
| 4-7 | 10 |
| 8+ | 5 |

目标：单次调度总抓取量不超过 200 条，避免耗时过长和触发限速。

## 生成调度配置

展示建议并获得用户确认后，更新 `config.yaml` 的 `scheduler` 段。

### scheduler.jobs 格式

每个 job 对应一个 cron 任务：

```yaml
scheduler:
  enabled: true
  jobs:
    - name: "daily_youtube_search"
      platform: "youtube"
      action: "search"
      query: "<keyword>"
      cron: "0 8 * * *"
      limit: 10
```

**注意：** 每个 job 只能绑定一个关键词。如果有多个关键词，需要为每个关键词创建独立的 job，或创建一个脚本遍历关键词。

建议方案：为每个 `platform × keyword` 组合创建一个 job，job name 格式为 `<platform>_<keyword的slug>`。如果组合数量过多（> 20），建议与用户讨论是否精简关键词或平台。

## 管理操作

### 查看当前调度

```bash
data-factory --config config.yaml schedule list
```

### 启动调度器

```bash
data-factory --config config.yaml schedule start
```

调度器以前台阻塞方式运行。提示用户：
- 可在新终端窗口中启动
- 按 Ctrl+C 停止
- 如需后台运行，可使用系统的任务管理工具（如 nohup、screen、Windows 任务计划程序）

### 修改调度

直接编辑 `config.yaml` 的 `scheduler.jobs` 段。修改前向用户确认变更内容。

## 自适应调整

每轮抓取汇总后评估调度合理性：

### 降低频率

**触发条件：** 某平台连续 3 次调度搜索，新增条目均为 0。

```
<platform> 连续 3 次搜索没有新内容。
建议将频率从 <当前> 调整为 <建议>。要调整吗？
```

### 提高频率

**触发条件：** 某平台每次搜索都有大量新内容（> limit 的 80%）。

```
<platform> 每次搜索都接近上限，可能遗漏内容。
建议将频率从 <当前> 调整为 <建议>，或增加 limit。要调整吗？
```

### 主动建议

**触发条件：** Agent 启动时发现某启用平台超过 7 天未抓取。

```
<platform> 已经 <N> 天没有抓取了。要执行一次抓取吗？
```

所有调整均需用户确认后才修改配置。
```

- [ ] **Step 2: 提交**

```bash
git add modules/schedule.md
git commit -m "docs: add schedule module for cron job management"
```

---

### Task 8: 集成验证

**Files:**
- 无新文件

- [ ] **Step 1: 验证文件完整性**

确认以下文件全部存在：

```bash
ls SKILL.md modules/init.md modules/fetch.md modules/discover.md modules/experience.md modules/schedule.md knowledge/platform_quirks.md knowledge/experiences_template.md
```

预期：8 个文件全部存在，无报错。

- [ ] **Step 2: 验证交叉引用**

逐一检查各模块中引用的文件路径是否正确：

| 引用方 | 引用目标 | 检查 |
|--------|---------|------|
| `SKILL.md` | `modules/init.md` | 路径正确 |
| `SKILL.md` | `modules/fetch.md` | 路径正确 |
| `SKILL.md` | `modules/discover.md` | 路径正确 |
| `SKILL.md` | `modules/schedule.md` | 路径正确 |
| `SKILL.md` | `modules/experience.md` | 路径正确 |
| `SKILL.md` | `knowledge/platform_quirks.md` | 路径正确 |
| `modules/init.md` | `knowledge/experiences_template.md` | 路径正确 |
| `modules/init.md` | `modules/schedule.md` | 路径正确 |
| `modules/init.md` | `modules/fetch.md` | 路径正确 |
| `modules/fetch.md` | `modules/discover.md` | 路径正确 |
| `modules/fetch.md` | `knowledge/platform_quirks.md` | 路径正确 |
| `modules/experience.md` | `knowledge/experiences_template.md` | 路径正确 |
| `modules/experience.md` | `knowledge/platform_quirks.md` | 路径正确 |

- [ ] **Step 3: 验证 CLI 命令一致性**

对照 `data_factory/cli.py` 的实际命令，检查 `SKILL.md` CLI 速查表和各模块中的命令是否与 CLI 签名完全匹配。重点检查：

- 参数名称（`--config`、`--platform`、`--from`、`--force`、`--limit`、`--id`、`--all`）
- 位置参数顺序（`search <platform> <query>`、`fetch [url]`、`process <step>`）
- 子命令层级（`index rebuild`、`index status`、`schedule start`、`schedule list`）

- [ ] **Step 4: 运行已有测试确认无回归**

```bash
cd D:\git\data-factory
python -m pytest -v
```

预期：80 个测试全部通过（本次只新增了文档，不应影响测试）。

- [ ] **Step 5: 最终提交**

如有任何修正，统一提交：

```bash
git add -A
git commit -m "docs: complete data-factory AI Skill documentation"
```
