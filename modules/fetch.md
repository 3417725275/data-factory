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

> **⚠️ 串行执行**：逐平台、逐关键词串行执行搜索，每条命令等待完成后再执行下一条。
> 禁止并行启动多个 `search` 进程（opencli 共享同一个 Chrome 实例，并发会导致 tab 冲突）。

### 2.2 去重

遍历各平台的 `<platform>/index.json` 文件，收集所有已抓取条目的 `url` 字段，与搜索到的 URL 对比，过滤掉已存在的 URL。

如果平台目录下没有 `index.json`，先执行索引重建：

```bash
data-factory --config config.yaml index rebuild --all
```

> **注意**：`global_index.json` 仅存储各平台的条目数和更新时间，不含具体 URL。
> 去重必须读取各平台的 `index.json`（其中 `items` 字典的每个条目包含 `url` 字段），
> 或直接检查 `<platform>/<item_id>/meta.json` 是否存在。

### 2.3 全量抓取

将去重后的新 URL 直接作为参数传入 `fetch` 命令：

```bash
# 方式 1：多 URL 参数（推荐，无需临时文件）
data-factory --config config.yaml fetch "<url1>" "<url2>" "<url3>" ...

# 方式 2：从文件读取（URL 数量非常大时）
data-factory --config config.yaml fetch --from .fetch_urls.tmp
```

如果使用方式 2，抓取完成后删除临时文件。

> **⚠️ 关键：URL 必须原样传递，不得截断 query 参数**
>
> 搜索返回的 URL 可能包含鉴权参数（如小红书的 `xsec_token`），这些参数对成功抓取至关重要。
> 将 URL 传给 `fetch` 命令时，**必须保留完整的 query string**，不能只取路径部分。
>
> - ❌ `fetch "https://www.xiaohongshu.com/search_result/abc123"` → 返回"安全限制"
> - ✅ `fetch "https://www.xiaohongshu.com/search_result/abc123?xsec_token=xxx&xsec_source="` → 正常抓取
>
> 代码内部会自动进行 URL 规范化（如将 `search_result` 转为 `explore`），但会保留鉴权参数。

在内存中记录本轮抓取的 URL 列表，供关键词发现阶段使用。

> **⚠️ 串行执行**：不要为不同平台或不同 URL 并行启动多个 `fetch` 进程。
> 推荐将所有去重后的 URL 传入单条 `fetch` 命令（方式 1 或方式 2），命令内部会逐个串行处理。

**不暂停等待用户确认**，除非用户主动中断。

> **已存在条目的处理**：对于去重后仍传入 `fetch` 的已有条目（如去重遗漏），
> `data-factory` 不会重新抓取内容，而是自动触发评论刷新（`run_refresh`）。
> 如需强制重新抓取，使用 `--force` 参数。

## Step 3：错误处理

监控每条 `fetch` 命令的输出和退出码。对于失败的 URL：

1. **暂存失败记录**：将失败 URL + 平台 + 原因暂存在内存中，**不中断流程**，继续处理剩余 URL
2. **提取失败原因**：从 CLI 输出的 `ERROR`/`WARNING` 行中提取关键信息，结合 `knowledge/platform_quirks.md` 的已知问题做解释（如"yt-dlp: 年龄限制"、"xsec_token 缺失"等）
3. **记录经验**：按 `knowledge/experiences_template.md` 格式追加到 `experiences.md`
4. **检索方案**：
  - 搜索 `experiences.md` 中是否有同平台 + 同类错误的记录
  - 搜索 `knowledge/platform_quirks.md` 中是否有相关说明
5. **自动重试**（如果有可应用的方案）：
  - 超时类错误 → 建议用户调大 rate_limit，重试
  - 网络类错误 → 检查代理设置，重试
  - 其他错误 → 跳过，在汇总中标记
6. **跳过**（如果无方案）：保留在失败清单中，统一在 Step 5 汇总

> **⚠️ 关键**：所有 URL 处理完毕后统一进入 Step 5 汇总。不要因为某条 URL 失败就中断整个流程。

## Step 4：刷新评论

```bash
data-factory --config config.yaml refresh
```

此命令自动按退避策略判断哪些条目需要刷新。

## Step 5：抓取后汇总

> **⚠️ 每轮抓取结束后必须输出此汇总报告，即使全部成功也不可省略。**

输出汇总报告（**强制格式**）：

```
## 本轮抓取汇总

### 搜索
- 搜索关键词: <N> 个 × <M> 个平台
- 发现 URL: <total> 条（去重后新增 <new> 条）

### 统计
- 总计: X 条 URL
- 成功: Y 条
- 跳过(已存在): Z 条
- 失败: N 条

### 失败清单
> 如果本轮无失败，写"无"。如果有失败，**必须逐条列出，禁止省略或笼统描述**。

| 平台 | URL | 失败原因 | 可否重试 |
|------|-----|---------|---------|
| youtube | https://... | yt-dlp: 年龄限制，需登录 | 是(配置cookies后) |
| xiaohongshu | https://... | 安全限制(xsec_token缺失) | 是(使用完整URL) |

### 评论刷新
- 已刷新: <N> 条
- 未到期: <N> 条

### 后处理
- 转录完成: <N> 条
- 图片下载: <N> 条

### 经验沉淀
- 若某平台连续失败 ≥ 3 条且原因相同，总结规律，建议写入 experiences.md
```

**约束**：

- 失败清单中的"失败原因"从 CLI 输出的 ERROR/WARNING 行中提取，结合 `knowledge/platform_quirks.md` 的已知问题做人类可读的解释
- "可否重试"需给出具体操作建议（如"配置 cookies"、"使用完整 URL"、"无法重试"等）

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