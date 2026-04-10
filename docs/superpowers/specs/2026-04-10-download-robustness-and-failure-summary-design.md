# 各平台下载健壮性修复 + 失败汇总机制

> 日期: 2026-04-10
> 状态: 待实施

## 背景

data-factory 在实际使用中暴露出两类问题：

1. **部分平台的媒体下载链路存在静默失败**：小红书下载异常被吞、Twitter 下载缺 Referer header、YouTube/TikTok 用裸 yt-dlp 失败时原因不透明。
2. **Skill 缺少结构化的失败汇总机制**：Agent 每轮抓取结束后的报告中，失败信息过于笼统（"失败 N 条"），无法帮助用户定位问题。

## 范围

- 修复 4 个平台 adapter 的下载健壮性
- 更新 Skill 文档（`fetch.md`、`SKILL.md`、`platform_quirks.md`）
- 不改 CLI 接口或 `FetchResult` 数据结构
- 不增加 cookies_file 配置（YouTube/TikTok 已知限制标注在文档中）

## 一、各平台下载健壮性修复

### 1.1 小红书 (`adapters/xiaohongshu.py`)

**现状**：`_download_media` 中异常被 `except: continue` 吞掉，下载失败时静默。

**修复**：
- 捕获异常后 `log.warning` 记录具体 note_id 和错误信息
- 解析 `run_opencli("xiaohongshu", "download", ...)` 返回值，检查状态
- 如果所有媒体下载失败，在日志中明确记录

### 1.2 Twitter (`adapters/twitter.py`)

**现状**：Syndication API fallback 用 `requests.get` 下载 `pbs.twimg.com` 图片时未带 Referer，部分环境 403。

**修复**：
- 所有 HTTP 媒体下载增加 `headers={"Referer": "https://x.com/", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}`
- 下载失败时 `log.warning` 记录 URL 和 HTTP 状态码

### 1.3 YouTube / TikTok (`core/video.py`)

**现状**：`download_video` 返回 `None` 时调用方无法区分失败原因。

**修复**：
- 日志细化失败原因分类：
  - `yt-dlp not installed` → 已有
  - `No video formats found`（通常需要登录） → 新增具体提示
  - `sign in to confirm`（年龄限制） → 新增具体提示
  - `timed out` → 已有
  - 其他 stderr → 截取关键行输出
- 不改返回类型（仍 `Path | None`），保持 API 兼容

### 1.4 `knowledge/platform_quirks.md` 更新

新增/更新内容：
- YouTube：明确标注无 `opencli youtube download`，视频下载依赖裸 yt-dlp，年龄限制/版权/地区限制视频可能失败，Agent 应在汇总中如实报告
- TikTok：同上，且反爬更严格，无 cookies 时频繁失败
- 新增表格汇总哪些平台有 `opencli download`：

| 平台 | opencli download | 视频下载方式 |
|------|-----------------|-------------|
| Bilibili | 有 | `opencli bilibili download`（自动注入浏览器 cookies） |
| 小红书 | 有 | `opencli xiaohongshu download`（图片/视频） |
| YouTube | 无 | `yt-dlp`（裸调用，无 cookies） |
| TikTok | 无 | `yt-dlp`（裸调用，无 cookies） |
| Twitter | 有（但不稳定） | `opencli twitter download` + Syndication API fallback |

## 二、Skill 失败汇总机制

### 2.1 `modules/fetch.md` Step 3 错误处理增强

在现有"监控 ERROR 行"描述后补充：

- Agent 执行每条 `fetch` 命令后，检查 CLI 输出是否有 `ERROR` 或非零退出码
- 将失败 URL + 原因**暂存在内存中**，不中断流程，继续处理剩余 URL
- 所有 URL 处理完毕后统一进入 Step 5 汇总

### 2.2 `modules/fetch.md` Step 5 汇总模板改造

替换当前笼统的汇总模板为强制格式：

```
## 本轮抓取汇总

### 统计
- 总计: X 条 URL
- 成功: Y 条
- 跳过(已存在): Z 条
- 失败: N 条

### 失败清单
> 如果本轮无失败，写"无"。如果有失败，必须逐条列出，禁止省略。

| 平台 | URL | 失败原因 | 可否重试 |
|------|-----|---------|---------|
| bilibili | https://... | 视频需要大会员 | 否 |
| youtube | https://... | yt-dlp: 年龄限制，需登录 | 是(配置cookies后) |

### 经验沉淀
- 若某平台连续失败 ≥ 3 条且原因相同，总结规律，建议写入 experiences.md
```

约束：
- 每轮结束**必须**输出此汇总，全部成功时失败清单写"无"
- 禁止"部分失败"等笼统描述，必须逐条列出
- 失败原因从 CLI 输出的 ERROR/WARNING 行中提取，结合 `platform_quirks.md` 做解释

### 2.3 `SKILL.md` 核心规则第 8 条

在现有 7 条核心规则后追加：

> **8. 失败汇总**：每轮抓取结束后，必须输出完整的汇总报告（见 `modules/fetch.md` Step 5 模板）。失败的 URL 必须逐条列出平台、URL、具体失败原因和是否可重试，禁止省略或笼统描述。

## 涉及文件清单

| 文件 | 改动类型 |
|------|---------|
| `data_factory/adapters/xiaohongshu.py` | 代码修复：下载异常日志 |
| `data_factory/adapters/twitter.py` | 代码修复：Referer header |
| `data_factory/core/video.py` | 代码修复：失败原因细化 |
| `knowledge/platform_quirks.md` | 文档更新：各平台下载方式汇总 |
| `modules/fetch.md` | 文档更新：Step 3 + Step 5 模板 |
| `SKILL.md` | 文档更新：核心规则第 8 条 |
| `tests/adapters/test_xiaohongshu.py` | 测试适配 |
| `tests/adapters/test_twitter.py` | 测试适配（如有） |
