# ResearchDaily

ResearchDaily 是一套面向 HCI / UbiComp / Sensing，并覆盖 Health、AI、Robotics 和跨领域内容的学术早报系统。它把“发现候选论文—全文审阅—质量筛选—生成早报—网页归档”串成一条可重复运行的流程。

线上站点：[Research Daily · 学术早报](https://research-daily-brief.dynamiclatte1.chatgpt.site/)

## 项目结构

```text
config/                         兴趣、配额、质量阈值和来源配置
data/                           本地 SQLite 状态库（默认不提交）
briefs/                         每日 Markdown 早报（默认不提交生成文件）
scripts/research_daily.py       候选收集、全文审阅校验、去重、生成和归档
tests/                          Python 单元测试
sites/research-daily/site/      网页源文件和历史归档
sites/research-daily/worker/    Cloudflare Worker：网页、反馈 API、MCP
sites/research-daily/migrations D1 数据库迁移
sites/research-daily/scripts/  Worker 构建、预览和验证脚本
```

## 已实现的硬约束

- 论文只有在“已阅读全文”的结构化审阅写入数据库后才可能入选。
- 摘要、搜索片段和二手报道不能作为论文总结依据。
- 质量分低于配置门槛时宁可少推荐，不凑满数量。
- DOI、arXiv ID 或规范化标题身份用于永久去重；正式版和预印本不会重复占位。
- 每日总阅读预算默认 30 分钟，上限 35 分钟。
- 每篇保留完整作者、链接、平台、年份、引用指标来源和查询日期。
- 只保存元数据、全文访问入口和原创总结，不默认下载 PDF。
- 每期同时保留 `briefs/YYYY-MM-DD.md`、数据库推荐记录和网页日期归档；新一期不会覆盖旧内容。
- 同一天的任务意外重跑时复用已提交版本，不会把当天早报覆盖为空报告。

## 快速使用

```bash
python3 scripts/research_daily.py init
python3 scripts/research_daily.py collect-openalex --days 45
python3 scripts/research_daily.py list-candidates --limit 30
python3 scripts/research_daily.py record-review /path/to/full-text-review.json
python3 scripts/research_daily.py generate --date 2026-11-10 --commit
python3 scripts/research_daily.py export-site --date 2026-11-10
```

`record-review` 会拒绝 `full_text_read` 不为 `true` 的记录。推荐记录一旦以 `--commit` 写入，默认永不再次进入早报名额。

`export-site` 会创建 `sites/research-daily/site/archive/YYYY-MM-DD/index.html` 并刷新历史归档首页。已有日期默认视为不可变版本；只有显式使用 `--replace` 才会重建。

## 网页和反馈系统

每日固定显示四栏：核心兴趣 2–3 篇（会议优先）、邻近领域 1–2 篇、重量级内容 1–2 篇（Nature/Science 优先）、其他领域 1–2 篇。先满足最低 `2+1+1+1`，再在 30 分钟目标、35 分钟上限内加入额外文章。缺项会保留栏目并明确说明。

每篇新审阅在 `reviewer_notes` 中单独写一行 `topic: specific_topic`。同一研究问题须使用相同标签，生成器默认每栏最多一篇同主题、全刊最多两篇；选题时还需与前七期比较，轮换方向。不同来源或不同会议不等于不同主题。45 分钟是生成耗时目标，与读者阅读时间分别记录。

网页中的每篇论文都有一个开放反馈栏。用户可以直接写问题、判断、偏好、反对意见、希望增减的方向或其他阅读工具中的相关笔记，无需先选择类别，也没有应用层字数上限。只有用户主动提交的内容会被保存。

反馈通过 Worker 的 `/api/feedback` 写入 D1，并通过站点 MCP 暴露 `list_research_feedback`。后续早报先阅读原始反馈，再归纳其中的兴趣、反感、疑问、方法偏好和精读重点；存储时不要求用户分类。系统不会自动抓取 Gemini 的完整对话；如果希望利用 Gemini 中的关注点，可以手动粘贴相关问题片段。

构建和验证 Worker：

```bash
node sites/research-daily/scripts/build-worker.mjs
node sites/research-daily/scripts/validate-worker.mjs
node sites/research-daily/scripts/preview-worker.mjs 4173
```

构建产物写入 `sites/research-daily/dist/`，其中包含 Worker 入口、站点资源和 D1 migration。`dist/` 是可再生成的发布产物，不需要手工编辑。

正式数据库迁移以 `sites/research-daily/drizzle/` 的 SQL 和 `meta/_journal.json` 为准。Sites 打包工具将它们放入 `dist/.openai/drizzle/` 后应用；旧的 `migrations/` 文件仅保留作历史参考，不能替代该发布路径。

## 阅读偏好学习

项目 skill `.agents/skills/personal-paper-reading/` 用于从用户主动提供的共同阅读记录中学习。原始对话、候选解释和生效偏好分开保存在本地 `data/reading-preferences.sqlite`；原始导出文件可放在被 Git 忽略的 `data/reading-records/`。代码会同步到 GitHub，阅读记录及归纳结果不自动公开。

学习从空档案开始。大模型自己的回答风格、用户的一次追问或没有反对，都不能当成稳定偏好。推断偏好至少需要四篇不同论文、三个主题、三个阅读日期的支持，再由后来第五篇不同论文验证，并审阅替代解释和反例；达到计数也不会自动生效。这些门槛是保守的工程规则，不代表统计置信度。出现反证会暂停已生效偏好。具体格式和工作流见 skill 的 `references/record-format.md` 和 `references/learning-policy.md`。

```bash
python3 scripts/reading_preferences.py ingest /path/to/reading-record.json
python3 scripts/reading_preferences.py observe /path/to/preference-hypothesis.json
python3 scripts/reading_preferences.py inspect
python3 scripts/reading_preferences.py profile
```

每日早报读取 `profile` 返回的生效偏好，候选解释不参与个性化。记录可逐次提供，无需凑够数量；当前没有凭历史示例预填任何个人风格。

## 运行测试

```bash
python3 -m unittest discover -s tests -q
```

## 配置

- `config/interests.json`：兴趣权重、质量阈值、每日配额和阅读预算。
- `config/sources.json`：搜索主题、重点 venue 和权威来源注册表。
- `.agents/skills/academic-morning-brief/`：Codex 可自动发现的项目技能。

完整运行规则以项目技能为准。若全文需要机构订阅，技能会请求用户在浏览器中完成授权或登录；系统不会绕过付费墙，也不会未经要求把 PDF 保存到本地。

## Git 同步

本项目的 Git 远程仓库是：

```text
https://github.com/CJunette/ResearchDaily.git
```

配置远程并推送：

```bash
git remote add origin https://github.com/CJunette/ResearchDaily.git
git push -u origin main
```

运行状态库、生成的每日 Markdown 和本地缓存默认由 `.gitignore` 排除；配置、脚本、测试和网页/Worker 源码会纳入版本控制。

