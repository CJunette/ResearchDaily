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
- 每日预计阅读量默认约 30 分钟；这是读者侧估计，不是筛选硬上限。系统会报告实际预计总时长，合格文章不会因为超过这个估计而被跳过。
- 每篇保留完整作者、链接、平台、年份、引用指标来源和查询日期。
- 只保存元数据、全文访问入口和原创总结，不默认下载 PDF。
- 每期同时保留 `briefs/YYYY-MM-DD.md`、数据库推荐记录和网页日期归档；新一期不会覆盖旧内容。
- 同一天的任务意外重跑时复用已提交版本，不会把当天早报覆盖为空报告。

## 快速使用

```bash
python3 scripts/research_daily.py init
python3 scripts/research_daily.py discovery-plan
# Read and invoke the skill returned by discovery-plan; it produces candidates and annotations.
python3 scripts/research_daily.py import-candidates /path/to/catalog-candidates.json
python3 scripts/research_daily.py record-discovery /path/to/discovery-annotations.json
python3 scripts/research_daily.py list-candidates --limit 30
python3 scripts/research_daily.py record-review /path/to/full-text-review.json
python3 scripts/research_daily.py generate --date 2026-11-10 --commit
python3 scripts/research_daily.py export-site --date 2026-11-10
```

`record-review` 会拒绝 `full_text_read` 不为 `true` 的记录。推荐记录一旦以 `--commit` 写入，默认永不再次进入早报名额。

`export-site` 会创建 `sites/research-daily/site/archive/YYYY-MM-DD/index.html` 并刷新历史归档首页。已有日期默认视为不可变版本；只有显式使用 `--replace` 才会重建。

## 可替换的文献发现模块

早报 skill 通过 `config/discovery.json` 的 `skill` 路径调用独立的 `literature-discovery` skill。以后替换该路径并遵守新 skill 的候选/标注接口，即可更换发现方法，全文评估、配额与网页生成继续使用既有流程。

- 会议／专业论文库：按届、期次或发表批次推进，包含 IMWUT、TOCHI、PACMHCI 等专业出版物；元数据仍保留它们真实的期刊类型。
- 期刊路线：专指 Nature/Science 正刊及研究子刊，以及 Cell、PNAS、The Lancet 等影响力相近的期刊。浏览新增目录并轮换学科；来源路线与早报的四个栏目分别判断。
- 每次从不同 session／主题抽取有界批次初筛，预留少量探索比例。标题摘要仅用于判断是否值得精读；入选早报仍要求全文核验。
- SQLite 保存目录检查点、文章标注、理由、重试日期及已有元数据／笔记，不镜像全文库。`record-discovery` 写入当前状态；`discovery-plan --source-key KEY` 可查看来源标注。已推荐记录仍永久去重。

`discovery-plan` 负责解析 skill 和读取状态，不会自行抓取或理解论文。实际目录访问和初筛由运行该 skill 的代理使用可用浏览／检索工具完成；当前并没有为所有出版社实现专用爬虫。目录访问失败必须记录，不能把未枚举的目录标为完成。

固定关键词批量搜索默认关闭。OpenAlex 主要补全标识、引用与开放版本；确有方向缺口时可显式补充检索并在运行记录说明理由：

```bash
python3 scripts/research_daily.py collect-openalex --allow-keyword-fallback --query "gap-specific research question" --track robotics_hri --days 45
```

## 网页和反馈系统

新生成的早报固定显示五栏：核心兴趣 3–4 篇（会议优先）、邻近领域 2–3 篇、重量级内容 2–3 篇（Nature/Science 优先）、其他领域 1–2 篇（会议和期刊均可）、AI 新动向 0–1 篇。先满足原四栏最低 `3+2+2+1`，再考虑 AI 新动向和其他额外文章。30 分钟是读者侧的阅读量估计，不是硬性选刊上限；系统会报告预计总阅读时间，合格文章不会因超过这个估计而被跳过。AI 新动向从最近 30 天滚动窗口找最新可见内容，找不到合格候选时再扩大到 90 天，不要求必须是当天发布。第五栏为空不算原配额缺口。既有日期归档不自动改写。

`config/sources.json.journal_catalogs` 是明确到刊名、URL、轮换主题的期刊注册表，分为主要与轮换来源，不要求每天遍历全部期刊。第五栏从 arXiv 分类新增及可用的第三方推荐线索中发现 AI 新观点／新应用，正式推荐仍须阅读全文并达到质量门槛；展示“尚未经同行评审”和实际阅读版本。发现策略及引用来源见 `literature-discovery/references/ai-frontier.md`。推荐热度不是质量证据。

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
- `config/discovery.json`：可替换发现 skill 的路径、批次／探索参数和旧关键词策略开关。
- `.agents/skills/literature-discovery/`：目录优先的文献收集与初筛技能。
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

