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
