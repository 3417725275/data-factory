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
