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
