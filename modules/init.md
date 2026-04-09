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

> **⚠️ 串行执行**：逐平台串行执行试搜索，每条命令完成后再执行下一条，不要并行。

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

确认后生成三个文件：

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

**⚠️ 必须逐项询问用户以下配置（不可跳过）：**

1. **网络代理**：是否需要配置代理？如果需要，填入 `network.proxy`（格式：`http://host:port` 或 `socks5://host:port`）
2. **视频转录（Whisper API）**：是否有 OpenAI API Key 用于视频转录？
   - 如果有 → 设置 `transcribe.whisper_api.enabled: true` 并填入 `api_key`
   - 如果没有 → 保持 `enabled: false`，视频转录将仅依赖平台字幕
   - 提示用户：**启用了 YouTube/Bilibili/TikTok 等视频平台时，建议配置 Whisper API 以获得完整转录**
3. **GitHub Token**（仅启用了 GitHub 时）：是否有 Personal Access Token？

只有用户明确回答后才生成最终配置。

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
