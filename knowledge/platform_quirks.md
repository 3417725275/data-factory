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
