# Data-Factory AI Skill 设计规格

> 日期：2026-04-09
> 状态：已确认

## 概述

将 `data-factory` 多平台数据抓取工具包装为一个平台无关的 AI Skill（适用于 Cursor、Claude、Claude Code 及其他 AI Agent）。AI Agent 通过读取 `SKILL.md` 入口文件，在用户创建的话题文件夹中完成从关键词规划到持续数据抓取的全生命周期管理。

### 核心能力

- **深度引导初始化**：梳理关键词 → 试搜索验证 → 生成配置
- **自动化抓取**：搜索去重 → 全量抓取 → 处理 → 索引
- **关键词发现**：文本频率 + LLM 语义分析，每轮抓取后建议新关键词
- **经验自进化**：两层知识体系，项目级追加日志 + 仓库级提炼知识
- **调度全权管理**：自动建议调度计划并管理启停

## 文件组织（方案 B：主文件 + 模块拆分）

```
data-factory/                          # 仓库根目录
├── SKILL.md                           # Skill 入口：启动检查、阶段路由、核心规则、CLI 速查
├── modules/
│   ├── init.md                        # 首次引导流程
│   ├── fetch.md                       # 搜索与抓取操作
│   ├── discover.md                    # 关键词发现与建议
│   ├── schedule.md                    # 调度建议与管理
│   └── experience.md                  # 经验记录与检索
├── knowledge/
│   ├── platform_quirks.md             # 仓库级：提炼后的平台经验（跨项目共享）
│   └── experiences_template.md        # 经验记录格式模板
├── data_factory/                      # 源码（已有）
├── tests/                             # 测试（已有）
├── config.example.yaml                # 配置示例（已有）
└── pyproject.toml                     # 项目定义（已有）
```

AI 只需读取 `SKILL.md`，按需加载 `modules/*.md` 和 `knowledge/*.md`。对于不支持文件读取的纯对话 AI，`SKILL.md` 开头会说明需将哪些模块文件一并提供。

## 项目工作空间结构

用户在任意位置创建话题文件夹（如 `D:\research\AI\`），Agent 引导初始化后生成：

```
D:\research\AI\
├── README.md                    # 项目说明（给 AI 和人读，含实时统计）
├── config.yaml                  # 项目配置（关键词、平台、调度等）
├── experiences.md               # 项目级经验日志（追加式）
├── youtube/                     # 按平台分目录
│   ├── index.json               # 平台索引（按 item_id 索引）
│   └── <video_id>/
│       ├── meta.json            # 元数据（含评论刷新状态）
│       ├── description.txt
│       ├── comments.json
│       ├── transcript.json      # 转录结果
│       └── assets/
│           └── thumbnail.jpg
├── bilibili/
│   └── ...
├── reddit/
│   └── ...
└── global_index.json            # 全局汇总索引
```

### config.yaml 结构

在 `data-factory` 标准配置的基础上增加 `project` 段：

```yaml
project:
  name: "AI"
  description: "AI领域多平台数据抓取"
  keywords: ["AI agent", "大模型", "LLM tutorial", "RAG", "向量数据库"]
  created_at: "2026-04-08T10:00:00+08:00"

output_dir: "."    # 当前话题目录即输出根目录

# 以下同 data-factory 标准格式
transcribe: ...
platforms: ...
scheduler: ...
network: ...
```

> **注意**：`project` 段是 Skill 层面使用的元数据，由 Agent 读取和维护。`data-factory` CLI 加载 YAML 时会忽略未知字段，不会冲突。不需要修改 `data-factory` 源码来支持 `project` 段。

### README.md

由 Agent 初始化时自动生成，包含：

- 项目话题和研究目的
- 当前关键词列表
- 启用的平台和各平台数据量概况
- 目录结构说明
- 配置文件和经验文件的位置与用途

Agent 每轮操作结束后自动更新统计信息（各平台条目数、最后抓取时间、关键词变更记录），确保任何时候读取都反映当前状态。

## SKILL.md 入口设计

### Phase 0：前置检查

Agent 读取 SKILL.md 后执行启动检查清单：

1. 确认 `data-factory` CLI 可用（`data-factory --help`）
2. 读取仓库级知识 `knowledge/platform_quirks.md`
3. 在用户当前工作目录下查找 `config.yaml`
   - 找到 → 读取配置 + `experiences.md`，进入「已有项目」路由
   - 未找到 → 进入「首次引导」路由（`modules/init.md`）

### 阶段路由

| 场景 | 路由目标 | 说明 |
|------|---------|------|
| 工作目录无 `config.yaml` | `modules/init.md` | 首次引导 |
| 用户要抓取/搜索 | `modules/fetch.md` | 搜索与抓取 |
| 一轮抓取结束 | `modules/discover.md` | 关键词发现 |
| 用户提到定时/调度 | `modules/schedule.md` | 调度管理 |
| 抓取出错或用户反馈问题 | `modules/experience.md` | 经验记录与检索 |

### 核心规则（硬性约束）

- 修改 `config.yaml` 前必须向用户确认
- 不自动删除已抓取的数据
- 新关键词建议必须经用户同意才写入配置
- 每次启动时读取 `experiences.md` 和 `platform_quirks.md`
- 每轮操作结束后自动更新 `README.md` 统计信息

### CLI 速查表

SKILL.md 末尾附完整 `data-factory` 命令参考：

```
data-factory --config <path> search <platform> "<query>" [--limit N]
data-factory --config <path> fetch "<url>" [--platform P] [--force]
data-factory --config <path> fetch --from <file>
data-factory --config <path> refresh [--platform P] [--id ID] [--force]
data-factory --config <path> process <transcribe|images> --platform P [--id ID]
data-factory --config <path> status [--platform P] [--id ID]
data-factory --config <path> index rebuild <--all | --platform P>
data-factory --config <path> index status [--platform P]
data-factory --config <path> import --platform P <source>
data-factory --config <path> schedule start
data-factory --config <path> schedule list
```

## 首次引导流程（modules/init.md）

### Step 1：了解话题

Agent 询问用户研究话题和目的。

### Step 2：梳理关键词

Agent 用 LLM 能力头脑风暴候选关键词（中英文混合），展示给用户挑选和补充。关键词为简单数组，不区分语言。

### Step 3：选择平台

展示所有可用平台（YouTube、Bilibili、Reddit、小红书、知乎、Twitter/X、TikTok、Discourse、GitHub），根据话题属性建议启用哪些，用户确认。

### Step 4：试搜索验证

用确定的关键词在各平台执行小范围搜索（`--limit 3`），展示结果摘要让用户判断方向。方向不对则回到 Step 2 调整。

### Step 5：生成配置

确认后生成三个文件：

- `config.yaml`：含 `project` 段 + 平台配置 + 网络配置
- `README.md`：项目说明
- `experiences.md`：空模板，含格式说明头

同时询问代理、API Key 等敏感配置。

### Step 6：建议调度计划

根据平台和关键词数量建议调度方案（详见调度管理段），用户确认后写入配置。

### Step 7：首轮抓取

询问用户是否立即执行首轮抓取，同意则转入 `modules/fetch.md`。

## 抓取操作流程（modules/fetch.md）

### Step 1：加载上下文

读取 `config.yaml`（关键词 + 平台）、`experiences.md`、`platform_quirks.md`。

### Step 2：搜索并全量抓取

遍历关键词 × 平台执行搜索，与 `global_index.json` 对比去重，新 URL 直接全量抓取，不暂停等待用户确认。

```bash
data-factory --config config.yaml search <platform> "<keyword>" --limit <N>
data-factory --config config.yaml fetch --from <temp_urls.txt>
```

Agent 记录本轮抓取的 URL 列表（内存中维护即可），用于后续关键词发现阶段识别"本轮新增内容"。

如用户需要选择性抓取，可主动中断默认流程。

### Step 3：错误处理

1. 记录失败到 `experiences.md`
2. 查阅 `platform_quirks.md` 和 `experiences.md` 检索已知解决方案
3. 有方案 → 尝试应用（如调整 rate_limit），重试
4. 无方案 → 跳过，最终汇总中标记失败

### Step 4：刷新评论

```bash
data-factory --config config.yaml refresh
```

### Step 5：抓取后汇总

输出汇总报告（新抓取数、失败数、评论刷新数、转录完成数、图片下载数），然后自动触发关键词发现（`modules/discover.md`）并更新 `README.md` 统计信息。

## 关键词发现（modules/discover.md）

每轮抓取结束后自动触发，也可由用户主动要求。

### Step 1：文本频率分析

扫描本轮新抓取内容（`meta.json` 标题/标签、正文、`platform_meta` 中的标签字段），提取高频出现但不在当前关键词列表中的词汇。

### Step 2：LLM 语义分析

Agent 自身即为 LLM，直接对本轮标题列表 + 高频词进行语义分析：相关子话题、新术语/项目名/工具名、关键词冗余或覆盖不足。不需要额外调用外部 LLM API。

### Step 3：汇总建议

合并去重，一条消息呈现建议（高频新词 + 相关子话题 + 冗余提示）。

### 约束

- 每轮最多建议 10 个新关键词
- 本轮新增内容 < 5 条时跳过发现流程
- 用户明确同意的关键词才写入 `config.yaml` 的 `project.keywords`，同步更新 `README.md`

## 经验管理（modules/experience.md）

### 两层知识体系

| 层级 | 文件 | 位置 | 作用域 |
|------|------|------|--------|
| 项目级 | `experiences.md` | 话题工作目录 | 单个项目的操作日志 |
| 仓库级 | `knowledge/platform_quirks.md` | data-factory 仓库 | 跨项目共享的平台知识 |

### 记录触发条件

- 抓取失败或超时
- 遇到新的平台行为（返回格式变化、API 限制变化）
- 用户纠正了 Agent 的操作方式
- 某个操作异常缓慢
- 重试后成功的解决方案

### 记录格式

```markdown
### YYYY-MM-DD HH:MM

- **平台**: <platform>
- **操作**: <action>
- **现象**: <observation>
- **解决**: <solution>
- **教训**: <lesson>
- **可复用**: 是/否
- **自动应用**: <auto_apply_rule>
```

### 读取时机

- Agent 每次启动时读取两份文件
- 抓取出错时检索匹配的已知问题
- 用户提问时

### 自动提炼规则

同一平台 + 同一类问题在 `experiences.md` 中出现 ≥ 3 次时，Agent 提示提炼到 `knowledge/platform_quirks.md`。用户确认后执行。

## 调度管理（modules/schedule.md）

### 触发场景

- 首次引导 Step 6
- 用户主动要求设置/调整调度
- Agent 发现某平台长时间未抓取时主动建议

### 建议依据

| 因素 | 影响 |
|------|------|
| 关键词数量 | 多 → 降低单次 limit 或分批 |
| 平台特性 | 实时性强（Twitter/Reddit）频率高；慢变（GitHub）频率低 |
| rate_limit 设置 | 间隔大的平台不宜高频 |
| 历史经验 | 频繁超时 → 降低频率或换时段 |

### 默认建议模板

| 平台 | 默认建议 |
|------|---------|
| YouTube / Bilibili | 每天 1 次 |
| Reddit / Twitter | 每天 1-2 次 |
| GitHub | 每 3 天 1 次 |
| Discourse | 每 2 天 1 次 |
| 评论刷新 | 每天 1 次 |

### 自适应调整

每轮抓取汇总后评估：

- 某平台连续 3 次搜索新增为 0 → 建议降低频率
- 某平台每次都有大量新内容 → 建议提高频率
- 调整建议需用户确认后才修改配置

### 管理命令

- 查看：`data-factory --config config.yaml schedule list`
- 启动：`data-factory --config config.yaml schedule start`
- 修改：Agent 编辑 `config.yaml` 的 `scheduler.jobs`（修改前向用户确认）
