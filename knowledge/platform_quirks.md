# 平台经验知识库

> 本文件由 data-factory Skill 维护，记录跨项目通用的平台特性和已知问题。
> Agent 每次启动时读取本文件，避免重复踩坑。
> 当同一问题在项目级 `experiences.md` 中出现 ≥ 3 次时，应提炼到本文件。

## YouTube

- `opencli youtube search` 返回的 URL 格式为 `https://www.youtube.com/watch?v=<id>`
- 评论抓取在高峰期（UTC 14:00-20:00）可能超时，建议 rate_limit ≥ 2.0
- 部分视频禁用了评论，`fetch_comments` 会返回空列表而非报错
- 视频下载使用 `yt-dlp`，需要 `ffmpeg` 合并音视频流；无 ffmpeg 时自动降级为预合并格式
- `opencli youtube transcript` 可获取字幕，保存为 `transcript.txt`

## Bilibili

- `opencli bilibili search` 返回的 URL 格式为 `https://www.bilibili.com/video/<BVid>`
- B站有反爬机制，建议 rate_limit ≥ 1.0，连续抓取超过 50 条可能触发验证码
- 部分视频需要登录才能查看完整评论
- 视频下载使用 `yt-dlp`（同 YouTube，需 ffmpeg 合并）
- 字幕使用 `opencli bilibili subtitle <BVid>` 获取
- `opencli bilibili` 没有专门的视频信息命令，用 `search <BVid> --limit 1` 做最佳匹配

## Reddit

- `opencli reddit search` 返回的 URL 格式为 `https://www.reddit.com/r/<sub>/comments/<id>/...`
- Reddit API 对未认证请求有严格限流，建议 rate_limit ≥ 2.0
- 评论树结构较深，抓取时间可能较长

## 小红书

- `opencli xiaohongshu` 依赖特定 cookie 或登录态，可能需要定期更新
- 图片 URL 有防盗链，下载时需要带 referer header
- **URL 规范化**：搜索结果 URL 含 `/search_result/`，需转为 `/explore/` 格式才能被 `opencli` 正确处理
- **⚠️ xsec_token 不可丢弃**：搜索返回的 URL 包含 `?xsec_token=xxx&xsec_source=` 等鉴权参数，这些参数是小红书验证请求合法性的必要凭据。如果截断这些参数，`opencli` 将返回"安全限制"（title="安全限制"、content="访问链接异常"），内容、评论、图片全部为空。**传给 fetch 时必须保留完整的 query string**
- **资源目录展平**：`opencli xiaohongshu download` 会在 `assets/` 下创建以 note_id 命名的子目录，需自动展平到 `assets/` 根目录
- Windows 上 URL 含 `&` 等特殊字符时需要显式引号包裹（`shell=True` 场景）

## 知乎

- `opencli zhihu search` 返回结果混合了问题和文章，`title` 字段可用
- **两种内容类型**：
  - 问答（`zhihu.com/question/...`）：用 `opencli zhihu question <numeric_id> --limit 10` 获取回答
  - 文章（`zhuanlan.zhihu.com/p/...`）：用 `opencli zhihu download --url <url>` 导出 Markdown
- **问答标题获取策略**（按优先级）：
  1. 搜索缓存（`.search_cache.json`，搜索阶段自动写入）
  2. CDP 连接 opencli 的 Chrome 实例，读取 `h1.QuestionHeader-title` DOM 元素
  3. HTTP 请求页面 `<title>` 标签（部分页面返回 403）
  4. 从第一条回答智能截断生成标题（最后兜底）
- **CDP 端口动态发现**：opencli 启动的 Chrome 调试端口不固定，通过扫描进程命令行参数中的 `--remote-debugging-port` 获取
- **文章 UI 噪音**：`opencli zhihu download` 导出的 Markdown 含"复制为Markdown"、"下载为 ZIP"等 UI 文字，需用正则清理
- **资源目录展平**：同小红书，文章下载可能创建子目录，需展平
- 评论功能尚未在 opencli 中实现

## Twitter/X

- `opencli twitter` 需要有效的 API 凭证
- rate_limit 建议 ≥ 2.0，Twitter API 限制较严

## TikTok

- 视频下载依赖 `yt-dlp`（通过 `core.video.download_video` 统一调用），需确保已安装
- 评论功能尚未在 opencli 中实现

## Discourse

- 使用 REST API 直接访问，需要配置 `base_url`
- 不同 Discourse 实例的 API 版本可能不同，注意兼容性
- 搜索结果分页默认 50 条

## GitHub

- 使用 REST API，未认证时限速 60 次/小时，配置 token 后 5000 次/小时
- Issue 和 PR 的评论是分开的 API 端点
- 搜索 API 有独立限速（每分钟 30 次）

## 通用

- **⚠️ 串行执行（最重要）**：所有 `data-factory` CLI 命令必须逐条串行执行，禁止并发。`opencli` 依赖单一 Chrome 浏览器实例，同时运行多个命令会导致 "No tab with id"、"No window with id" 等 tab 冲突错误。搜索、抓取、刷新均需等待上一条命令完成后再执行下一条
- **ffmpeg**：YouTube / Bilibili / TikTok 视频下载后需要 ffmpeg 合并音视频流。缺少 ffmpeg 时自动降级为 `best[ext=mp4]` 预合并格式（画质可能较低）
- **Windows `shell=True`**：在 Windows 上调用 `opencli`（.cmd 文件）时必须用 `shell=True`，且 URL 中的 `&` 等特殊字符需显式引号包裹
- **编码**：Windows 默认 GBK 编码，subprocess 调用需指定 `encoding="utf-8", errors="replace"`
- **opencli 激活**：首次使用需运行 `opencli doctor` 激活浏览器桥接，如未桥接需等待 4s 后重试，最多 3 次
