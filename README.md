# data-factory

多平台数据抓取工具。支持从 9 个平台抓取结构化内容，每条记录存储为独立文件夹，包含原生格式的内容文件和 JSON 元数据。

## 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone <repo-url>
cd data-factory

# 创建虚拟环境并安装
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -e .
```

### 2. 配置

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，填入你的 API Key 等信息（详见下方「配置说明」）。

### 3. 使用

```bash
# 搜索平台内容
data-factory --config config.yaml search youtube "LLM tutorial" --limit 5

# 抓取单个 URL
data-factory --config config.yaml fetch "https://www.youtube.com/watch?v=xxx"

# 从文件批量抓取（每行一个 URL）
data-factory --config config.yaml fetch --from urls.txt

# 强制重新抓取（忽略已抓取标记）
data-factory --config config.yaml fetch --force "https://www.youtube.com/watch?v=xxx"

# 刷新评论（自动按退避策略判断哪些需要刷新）
data-factory --config config.yaml refresh

# 强制刷新所有评论
data-factory --config config.yaml refresh --force

# 查看整体状态
data-factory --config config.yaml status

# 查看某条数据的详细状态
data-factory --config config.yaml status --platform youtube --id <video_id>

# 查看索引状态
data-factory --config config.yaml index status

# 重建全部索引
data-factory --config config.yaml index rebuild --all

# 重新执行转录处理
data-factory --config config.yaml process transcribe --platform youtube

# 重新下载图片
data-factory --config config.yaml process images --platform xiaohongshu

# 导入已有数据
data-factory --config config.yaml import --platform xiaohongshu export.json

# 启动定时调度器
data-factory --config config.yaml schedule start

# 查看调度任务列表
data-factory --config config.yaml schedule list
```

## 支持平台

| 平台 | 搜索 | 抓取 | 评论 | 媒体 | 抓取工具 |
|------|------|------|------|------|----------|
| YouTube | ✅ | ✅ | ✅ | ✅ 缩略图 | opencli |
| Bilibili | ✅ | ✅ | ✅ | ✅ 封面 | opencli |
| Reddit | ✅ | ✅ | ✅ | — | opencli |
| 小红书 | ✅ | ✅ | ✅ | ✅ | opencli |
| 知乎 | ✅ | ✅ | ⚠️ 待实现 | — | opencli |
| Twitter/X | ✅ | ✅ | ✅ | ✅ | opencli |
| TikTok | ✅ | ✅ | ⚠️ 待实现 | ✅ yt-dlp | opencli |
| Discourse | ✅ | ✅ | ✅ | — | REST API |
| GitHub | ✅ | ✅ | ✅ | — | REST API |

## 架构

```
抓取 (Fetch) → 处理 (Process) → 索引 (Index)

PlatformAdapter (抽象基类)
  ├── YouTubeAdapter      (opencli)
  ├── BilibiliAdapter     (opencli)
  ├── RedditAdapter       (opencli)
  ├── XiaohongshuAdapter  (opencli)
  ├── ZhihuAdapter        (opencli)
  ├── TwitterAdapter      (opencli)
  ├── TikTokAdapter       (opencli + yt-dlp)
  ├── DiscourseAdapter    (requests, 支持多实例: discourse_cn / discourse_en)
  └── GitHubAdapter       (requests)

Processor (抽象基类)
  ├── TranscribeProcessor (Whisper API → 本地 Whisper → 平台字幕)
  └── ImageDownloadProcessor
```

### 处理流程

1. **Fetch** — 适配器抓取内容，写入文件夹（正文、评论、元数据）
2. **Process** — 自动运行处理器（转录视频、下载图片），也可手动重跑
3. **Index** — 更新平台索引 `index.json` 和全局索引 `global_index.json`

## 输出目录结构

```
output/
├── youtube/
│   ├── index.json                  # 平台索引（按 item_id 索引）
│   └── <video_id>/
│       ├── meta.json               # 元数据（含评论刷新状态）
│       ├── description.txt         # 视频描述
│       ├── comments.json           # 评论数据
│       ├── transcript.json         # 转录结果（处理后生成）
│       └── assets/
│           └── thumbnail.jpg       # 缩略图
├── reddit/
│   ├── index.json
│   └── <post_id>/
│       ├── meta.json
│       ├── content.md              # 帖子正文（Markdown）
│       └── comments.json
├── zhihu/
│   ├── index.json
│   └── q_<question_id>/
│       ├── meta.json
│       ├── content.md              # 回答正文
│       └── comments.json
└── global_index.json               # 全局汇总索引
```

每个 `meta.json` 包含：
- **公共字段**：`id`、`platform`、`url`、`title`、`author`、`content_type`、`fetched_at`、`published_at`、`status`
- **处理状态**：`content_fetched`、`transcript_completed`、`images_downloaded`
- **评论刷新状态**：`comments_refresh`（间隔、下次刷新时间、连续未变次数）
- **评论历史**：`comment_history`（每次刷新的时间和评论数）
- **平台特有字段**：`platform_meta`（如播放量、点赞数、分区等）

## 评论智能刷新策略

采用指数退避策略，减少不必要的 API 调用：

| 连续未变次数 | 刷新间隔 |
|-------------|---------|
| 0（初始/有变化） | 每天 |
| 2 次未变 | 3 天 |
| 3 次未变 | 7 天 |
| 4+ 次未变 | 14 天（上限） |

一旦检测到评论数变化，立即重置为每天刷新。

## 配置说明

配置文件为 `config.yaml`，从 `config.example.yaml` 复制后修改。程序按以下优先级查找配置：

1. `--config` 命令行参数指定的路径
2. `DATA_FACTORY_CONFIG` 环境变量指定的路径
3. 当前目录下的 `config.yaml`

### 配置文件结构

```yaml
# 数据输出目录
output_dir: "./output"
log_level: "info"

# === 转录配置 ===
transcribe:
  whisper_api:
    enabled: true
    api_key: ""                              # OpenAI API Key
    model: "whisper-1"
    base_url: "https://api.openai.com/v1"    # 可替换为兼容 API 地址
  whisper_local:
    enabled: false
    model_size: "large-v3"                   # tiny / base / small / medium / large-v3
    device: "cuda"                           # cuda / cpu
  platform_subtitle:
    enabled: true                            # 是否回退到平台自带字幕

# === 平台配置 ===
platforms:
  youtube:
    enabled: true
    rate_limit: 2.0          # 请求间隔（秒）
  bilibili:
    enabled: true
    rate_limit: 1.0
  reddit:
    enabled: true
    rate_limit: 2.0
  xiaohongshu:
    enabled: true
    rate_limit: 1.5
  zhihu:
    enabled: true
    rate_limit: 1.5
  twitter:
    enabled: true
    rate_limit: 2.0
  tiktok:
    enabled: true
    rate_limit: 2.0
  discourse_cn:              # Discourse 实例（中文社区）
    enabled: true
    base_url: ""             # 填入社区 URL，如 https://discuss.example.cn
    rate_limit: 1.0
  discourse_en:              # Discourse 实例（英文社区）
    enabled: true
    base_url: ""             # 填入社区 URL，如 https://discuss.example.com
    rate_limit: 1.0
  github:
    enabled: true
    token: ""                # GitHub Personal Access Token（可选，提高 API 限额）
    rate_limit: 1.0

# === 定时调度 ===
scheduler:
  enabled: false
  jobs:
    # 示例：每天早上 8 点搜索 YouTube
    # - name: "daily_youtube"
    #   platform: "youtube"
    #   action: "search"
    #   query: "LLM tutorial"
    #   cron: "0 8 * * *"
    #   limit: 10

# === 网络配置 ===
network:
  proxy: ""                  # HTTP 代理，如 http://127.0.0.1:7890
  timeout: 30                # 请求超时（秒）
  retry: 3                   # 失败重试次数
```

### 环境变量覆盖

以下环境变量可覆盖配置文件中的对应值（优先级更高）：

| 环境变量 | 覆盖字段 | 说明 |
|---------|---------|------|
| `DATA_FACTORY_WHISPER_API_KEY` | `transcribe.whisper_api.api_key` | OpenAI API Key |
| `DATA_FACTORY_PROXY` | `network.proxy` | HTTP 代理地址 |
| `DATA_FACTORY_OUTPUT_DIR` | `output_dir` | 输出目录路径 |
| `DATA_FACTORY_CONFIG` | — | 配置文件路径（当 `--config` 未指定时） |

## 前置依赖

- **Python 3.11+**
- **[opencli](https://github.com/nicepkg/opencli)**：大部分平台的搜索和抓取依赖此工具
  ```bash
  npm install -g opencli
  ```
- **yt-dlp**（可选）：用于 TikTok 视频下载和音频提取
  ```bash
  pip install yt-dlp
  ```

## 开发

```bash
pip install -e ".[dev]"
pytest -v
```

> **注意：** 运行测试需要安装 `[dev]` 额外依赖（`pytest` 和 `pytest-mock`）。如果直接运行 `pytest` 而没有执行 `pip install -e ".[dev]"`，会因缺少 fixture 而报错。
