# TerraGuide

**泰拉瑞亚 AI 攻略搜索 · 三个月工作流程计划**

- 范围：仅支持 1.4 原版内容，不含 TModLoader 模组
- 周期：第 1 周 — 第 13 周（约 3 个月）
- 执行方式：按第 1–13 周滚动执行；周末用交付件及验收记录确认进度。CSDN 发文选题另见《TerraGuide CSDN 博客计划》。
- 基线：详见同目录 `terraguide_project_plan.md`

---

## 阶段总览

| 阶段 | 周次 | 核心产出 |
|------|------|----------|
| Phase 1　数据底座 | 第 1 - 4 周 | MediaWiki API 爬虫 + 数据清洗 + 切片 + ChromaDB 向量索引 + 纯向量基线 + 混合检索命中率 ≥ 80% |
| Phase 2　后端 RAG 引擎 | 第 5 - 8 周 | FastAPI + Ollama + 混合检索 + 游戏状态解析 + 进度映射表 + 全部 4 个 API + RAG 端到端覆盖率 ≥ 70% |
| Phase 2.5　RAG 基线对比 | 第 9 周 | A/B 两组 15 条测试问题对比表 + 博客素材 |
| Phase 3　前端界面 + Phase 4 部署 | 第 10 - 13 周 | React ChatBox + SourceCard + GameContext + SSE 流式 + Docker Compose + 公网部署 + HTTPS |

---

## 第 1 周 · 爬虫框架 + MediaWiki API 对接

**【Phase 1 · 数据底座】**

### 本周任务

- 调研 terraria.wiki.gg 的 MediaWiki API：测试 `action=query` 列分类成员、`action=parse` 获取页面正文
- 写 `categories.yaml`：白名单分类 + 排除关键词（Mod/Calamity 等）
- 搭爬虫主框架（`crawler/scrape.py`）：requests + 重试 + User-Agent + 1 秒请求间隔
- 写 API 遍历逻辑：按 `categories.yaml` 逐分类爬页面列表，逐页面抓正文 HTML
- 将 HTML 存入采集缓存目录，保留页面标题、来源 URL 与抓取结果；第 2 周再输出清洗后的 Markdown 和元数据。
- 验证：能否拿到至少 100 个页面的原始 HTML

### 本周交付物

- ✅ `crawler/scrape.py`（可运行，支持白名单过滤）
- ✅ `crawler/categories.yaml`
- 采集缓存中至少 100 个原版页面，以及包含成功、跳过、失败数量的试抓日志。

### 周末验收

试跑至少覆盖 Bosses、Weapons、Armor 三类；抽查已知模组条目不会进入输出，验证分页、限速及失败日志。

### 风险预判

API 可能限流 → 先用低频率测试；Playwright 作为兜底

---

## 第 2 周 · 全量爬取 + BeautifulSoup 清洗 + 元数据提取

**【Phase 1 · 数据底座】**

### 本周任务

- 按 Bosses、Weapons、Armor、Accessories、Items、NPCs、Game mechanics、Events、Progression guides 执行全量采集，试抓后补齐分页并记录失败页；原始采集量争取达到 2,000 页。
- 写 `crawler/parser.py`：API 返回的 HTML → BeautifulSoup 提取 `mw-parser-output` 正文
- 移除：导航框、编辑链接、广告、Mod 模板、折叠框默认内容
- 解析 Infobox（BOSS 属性、物品属性）为结构化键值对
- 解析合成配方表格（Crafting Station + 材料 → 产物）
- 提取 `title`、`category`、`url`、`aliases`、`is_hardmode`、`boss_stage`；按 Wiki 标签识别肉前与硬模式内容，无法确认的条目标记待核对。
- 输出 `.md` 正文 + 同名 `.json` 元数据到 `crawler/raw/`
- 验证：随机抽 20 个页面检查清洗质量（无导航栏、Infobox 可读）

### 本周交付物

- ✅ `crawler/parser.py`
- `crawler/raw/` 下至少 1,500 个去重后的原版页面，每页包含 Markdown 正文及对应 JSON 元数据。
- ✅ 清洗质量抽查报告（20 页）

### 周末验收

用统计脚本确认 ≥ 1,500 个去重后的原版页面；跨类别抽查 20 页，记录正文、属性、配方、来源与阶段标签的缺失情况。

### 风险预判

某些页面 Infobox 格式不统一 → 多写几个 fallback 正则

---

## 第 3 周 · 文档切片 + bge-m3 embedding + ChromaDB 入库

**【Phase 1 · 数据底座】**

### 本周任务

- 写 `crawler/chunker.py`：按 `##` 二级标题切分，chunk 500-800 tokens，overlap 100 tokens
- 写 `crawler/embed.py`：sentence-transformers 加载 bge-m3（~2GB，首次运行需下载）
- 离线批量生成 bge-m3 文档向量，保留为质量对照；不在后端默认常驻 bge-m3。
- 用 all-MiniLM-L6-v2 对同批文档另建轻量索引；线上查询用同一模型实时编码，禁止将 MiniLM 查询与 bge-m3 文档向量直接比较。
- 编写 `crawler/ingest.py`，持久化 ChromaDB：默认轻量集合 `terraria_wiki_v1`，bge-m3 对照集合单独存储。
- ChromaDB 元数据字段必须包含：`title`、`category`、`is_hardmode`、`aliases`
- 检查集合可重启加载、条数与切片清单一致；约 8,000 chunks 为估算，不靠重复或过度切片凑数。

### 本周交付物

- ✅ `crawler/chunker.py`
- ✅ `crawler/embed.py`
- ✅ `crawler/ingest.py`
- ChromaDB 持久化索引、入库统计与建库配置（模型、维度、集合名、切片版本）。

### 周末验收

重启后可从持久化目录查询；抽查切片可回溯到标题和 URL；用同模型的查询分别在两个集合中完成冒烟测试。

### 风险预判

内存不足时先减小离线编码批次；如更换模型，必须重建相应集合，并使用同模型重新跑检索评估。

---

## 第 4 周 · 纯向量检索基线 + 混合检索实现 + 命中率 ≥ 80%

**【Phase 1 · 数据底座（收尾）】**

### 本周任务

- 准备 20 条测试查询（含专有名词：Zenith、天顶剑、Guide Voodoo Doll、机械三王召唤物、Spider Armor）
- 从 20 条查询中预先固定 10 条跑纯向量 Top-10 基线，逐条记录正确页面是否命中；纯向量不设硬门槛。
- **实现关键词检索**：从用户输入提取中英文专有名词（预先维护词典）→ 精确匹配 ChromaDB `title`/`aliases` 元数据 → 分数加权 +0.3
- 写 `crawler/search_eval.py`：自动化跑 20 条查询，输出 Top-5 召回 + 命中率统计
- 跑混合检索（向量 + 关键词），验证 Top-5 命中率 ≥ 80%
- 如果命中率不够：增加同义词词典、调 chunk size、调关键词加权分数
- 同一组 20 条查询以 Top-5 补跑纯向量对照，报告同口径结果；单列 10 条 Top-10 基线，避免直接拿不同口径的数字比较。

### 本周交付物

- ✅ `crawler/search_eval.py`
- ✅ 纯向量检索基线命中率数字（面试素材）
- ✅ 混合检索命中率 ≥ 80% 证明
- ✅ ChromaDB 索引最终版

### 周末验收

固定 20 条查询的正确页面，混合检索 Top-5 至少命中 16 条；若不达标，先修检索并复测，再进入后端阶段。

### 风险预判

混合检索仍达不到 80% → 考虑加更多同义词、缩短 chunk size、增加 rerank

---

## 第 5 周 · FastAPI 骨架 + Ollama 集成 + ChromaDB 混合检索服务

**【Phase 2 · 后端 RAG 引擎】**

### 本周任务

- 搭 `backend/` 目录结构 + `requirements.txt` + `Dockerfile`
- 写 `backend/app/config.py`：配置常量（模型名、端口、ChromaDB 路径）
- 写 `backend/app/services/llm.py`：Ollama HTTP 客户端封装（`/api/chat` + `/api/embeddings`）
- 本地启动 Ollama：`ollama serve && ollama pull qwen2.5:3b`
- 写 `backend/app/services/vectorstore.py`：ChromaDB 连接 + 混合检索（复用第 4 周的逻辑）
- 默认用 MiniLM 实时编码查询并使用相应集合；Ollama 嵌入仅作可选方案，切换时查询与文档必须使用同一嵌入模型。
- 写 `backend/app/main.py`：FastAPI 入口 + CORS + 健康检查（返回 Ollama + ChromaDB 状态）
- 本地 `curl` 测试 `/api/health`

### 本周交付物

- ✅ `backend/app/main.py` 可启动
- ✅ `GET /api/health` 返回 Ollama ready + ChromaDB chunks 数量
- ✅ Ollama qwen2.5:3b 模型本地拉取完成

### 周末验收

本地启动后调用 `/api/health`：就绪时返回 Ollama 和 ChromaDB 状态；停掉 Ollama 后能诊断异常；用同一索引复现第 4 周检索样例。

### 风险预判

启动时核对集合模型和维度配置；Ollama 不可用或模型未拉取时，健康检查返回明确原因。

---

## 第 6 周 · 游戏状态解析 + 进度映射表 + 核心 RAG 编排

**【Phase 2 · 后端 RAG 引擎】**

### 本周任务

- 写 `backend/app/core/game_state.py`：规则引擎（关键词词典 + 正则）提取 游戏进度/职业/难度/预算
- 写 `backend/app/core/progression.py`：进度 → 允许的 Wiki 分类/标签 映射表（Python dict）
- 写 `backend/app/core/rag.py`：完整 RAG 编排
- `rag.py` 流程：用户输入 → game_state 解析 → progression 查表 → ChromaDB `where` 条件过滤 + 混合检索 → Top 10
- 写 `backend/app/core/prompts.py`：System Prompt 模板（含修正后的原版时间线）
- `rag.py` 拼 Prompt → 调 Ollama `/api/chat`
- 后端本地直接 HTTP 测试完整 RAG 流程（不走前端）

### 本周交付物

- ✅ `backend/app/core/rag.py` 完整 RAG 管道可运行
- 提供可复现问答案例：肉后初期召唤师问题返回符合进度的候选（例如蜘蛛套），并可追溯到 Wiki 片段。
- ✅ 游戏状态解析 10 条测试用例全过

### 周末验收

10 条规则用例覆盖四个提取字段及未知状态；对比肉前与肉后召唤师问题，确认不会返回当前进度拿不到的装备。

### 风险预判

游戏状态解析规则漏命中 → 持续扩充词典；80% 场景规则够用，不用 LLM 抽取

---

## 第 7 周 · API 接口（/chat + /chat/stream SSE）+ 参考答案 + 迭代

**【Phase 2 · 后端 RAG 引擎】**

### 本周任务

- 写 `backend/app/api/chat.py`：`POST /api/chat`（同步）
- 写 `backend/app/api/chat.py`：`POST /api/chat/stream`（SSE 流式）
- SSE 事件格式：thinking → token → sources → done
- `GET /api/sources`：返回索引统计
- 准备 15 条 RAG 端到端测试问题（同 `terraguide_project_plan.md` 第八节）
- 跑完整 RAG 流程，人工评估 15 条问题核心要点覆盖率 ≥ 70%
- 如果不够：调 Prompt、调检索 Top-K、调关键词词典
- 有依据的攻略答案须附真实 Wiki 来源 URL；资料不足时明确说明，不编造答案或链接。

### 本周交付物

- ✅ 全部 4 个 API 端点可用
- ✅ SSE 流式输出正常（`curl -N` 能看到逐步 token）
- ✅ RAG 端到端覆盖率 ≥ 70%

### 周末验收

记录四个路由的请求/响应；用 `curl -N` 验证 token 逐步抵达、sources 与 done 正常；15 问要点覆盖率 ≥ 70%，附逐题评分。

### 风险预判

覆盖率不够 → 先检查检索召回率，再调 Prompt，最后考虑换 7B 模型

---

## 第 8 周 · 性能优化 + Prompt 精调 + 多轮对话

**【Phase 2 · 后端 RAG 引擎（收尾）】**

### 本周任务

- 多轮对话：messages 列表保留最近 3 轮，超过截断（不用 LangChain Memory）
- 首 token 延迟测试：纯 CPU 下确保 ≤ 10 秒
- 如果首 token 太慢：减少检索 Top-K、简化 Prompt 长度、换更快模型
- Prompt 精调：让 AI 回答更分点、更简洁、来源标注更清晰
- 后端 FastAPI Dockerfile 完善
- 后端本地用 uvicorn 长时间运行（1 小时）观察内存使用
- 给后端加简单日志（每请求记录检索耗时 + 生成耗时）

### 本周交付物

- 提交 1 小时运行记录，列出内存趋势和异常；如观察到持续增长，保留复现步骤并登记待修项。
- ✅ 纯 CPU 端到端响应 ≤ 20 秒，首 token ≤ 10 秒
- ✅ 多轮对话正确延续上下文

### 周末验收

用超过三轮的追问验证截断；在记录硬件、模型、提示词与输出长度后复测 CPU 首 token ≤ 10 秒、端到端 ≤ 20 秒，报告冷/热启动和未达标项。

### 风险预判

内存持续增长 → 检查 ChromaDB 查询是否缓存过多；重启 Ollama 清理 GPU 内存

---

## 第 9 周 · A/B 对照实验 + 输出对比表 + 博客素材

**【Phase 2.5 · RAG 基线对比（面试/博客素材）】**

### 本周任务

- 写 `eval/baseline.py`：无 RAG 纯 LLM 基线（只把用户问题发给 Ollama，不查 Wiki）
- 写 `eval/test_cases.json`：15 条测试问题 + 每条的期望核心要点（3-5 个）
- 写 `eval/compare.py`：批量跑 A/B 两组，自动评分（核心要点匹配）
- 输出：A 组（无 RAG）要点覆盖率 vs B 组（有 RAG）要点覆盖率
- 选 3–5 个代表性案例，保留 RAG 改善、无改善或退化的情况；不因结果不符合预期而更换题目。
- 写成 Markdown 对比报告
- **这是面试时必问的亮点**，务必拿到一个清晰的数字对比

### 本周交付物

- ✅ `eval/compare.py` 输出的对比表
- ✅ 3-5 个具体 A vs B 例子（Markdown）
- ✅ 可用于面试展示的数据

### 周末验收

冻结 15 条问题及评分标准，两组使用相同模型、生成设置；报告要点覆盖率、名称准确性、进度匹配、引用表现，并注明具体差值。

### 风险预判

若 RAG 未明显改善，保留原题、模型配置和实际结果，区分召回失误、进度不匹配和生成遗漏。

---

## 第 10 周 · React 骨架 + ChatBox + Message + SourceCard

**【Phase 3 · 前端界面】**

### 本周任务

- `npm create vite@latest frontend -- --template react`
- 安装 tailwindcss，配置 `vite.config.js` proxy `/api` → `localhost:8000`
- 搭项目结构 + `App.jsx` + `main.jsx` + `index.css` + `tailwind.config.js`
- 写 `components/Message.jsx`：用户消息（右对齐）/ AI 消息（左对齐 + 打字光标）
- 写 `components/SourceCard.jsx`：AI 回答底部的 Wiki 来源卡片（可点击跳转）
- 写 `components/ChatBox.jsx`：滚动消息列表 + 输入框 + Enter 发送
- 写 `src/api/chatApi.js`：fetch `/api/chat` 封装
- 联调：前端能发送非流式请求、渲染 AI 回答和来源卡片

### 本周交付物

- ✅ React 前端可启动，能和后端通信
- ✅ ChatBox + Message + SourceCard 三个组件正常工作
- ✅ 快速提问后能看到分点回答 + 来源

### 周末验收

从浏览器提交真实问题，可同时渲染 Markdown 和可点击的来源；断开后端时有明确错误提示且保留输入。

### 风险预判

Vite 交互问题 → 用 `npm init vite@latest . -- --template react --yes`

---

## 第 11 周 · SSE 流式 + Sidebar + GameContext + 体验优化

**【Phase 3 · 前端界面】**

### 本周任务

- 使用 fetch + ReadableStream 调用 `POST /api/chat/stream`，按 SSE 事件解析增量数据并处理断流、取消和错误。
- `chatApi.js` 新增 `streamChat` 函数，逐步推送 token → ChatBox 打字机效果
- 写 `components/Sidebar.jsx`：新建对话 + 历史对话列表 + localStorage 持久化
- 写 `components/GameContext.jsx`：职业下拉 + 进度下拉 + 难度下拉 + 预算偏好
- Quick Prompts：4 个常见问题快捷按钮（Welcome 页面）
- Loading 状态：思考中 → 检索 Wiki → 整理答案 三段动画
- 实现暗色/亮色主题切换，检查 375px 移动端布局。

### 本周交付物

- ✅ SSE 流式输出打字机效果正常
- ✅ 完整前端 UI（Sidebar + ChatBox + GameContext + SourceCard）
- ✅ Welcome 页 4 个 Quick Prompts 可点击

### 周末验收

按 375px 和桌面两种视口验证逐字输出、手动选择游戏状态、新建对话、刷新后恢复历史、快捷提问及主题切换。

### 风险预判

SSE Nginx 缓冲问题 → 本地开发无 Nginx，生产 Nginx 需 `proxy_buffering off`

---

## 第 12 周 · 前端联调 + Docker Compose 编写 + Nginx 配置

**【Phase 3 · 收尾 + Phase 4 部署准备】**

### 本周任务

- 前后端完整联调：对话 → 流式回答 → 来源卡片可点 → 多轮对话 → 历史记录持久化
- 修复联调问题（CORS、类型转换、空来源、SSE 断流）；断流可手动重试且不得把重复消息写进历史。
- 写 `docker-compose.yml`：frontend + backend + ollama 三个服务
- `frontend/Dockerfile`（多阶段构建：node 编译 → nginx 托管）
- `frontend/nginx.conf`（静态 + `/api` 反代 + SSE 配置 + gzip）
- 后端 Dockerfile（`uvicorn app.main:app --host 0.0.0.0`）
- 本地 `docker compose build + up` 测试

### 本周交付物

- ✅ `docker-compose.yml` 可一键启动所有服务
- ✅ 前端 Nginx 能正确反代 `/api` 到后端
- ✅ 本地 Docker 部署测试通过

### 周末验收

按 README 从干净环境启动三个服务；检查容器状态、索引持久化、Nginx `/api` 转发及公网同类反代下的 SSE 不缓冲。

### 风险预判

Windows Docker Desktop 资源不够 → 分配 8GB+ 内存；Ollama 单独跑在主机

---

## 第 13 周 · 云服务器 + HTTPS + 公网访问 + 最终验收

**【Phase 4 · 部署上线】**

### 本周任务

- 确认云服务器及域名可用性，核对 CPU 起步规格（4 核、8GB RAM）及备案、DNS 或证书申请所需条件。
- 服务器装 Docker + Docker Compose
- 按 Compose 方案启动 Ollama 并拉取 qwen2.5:3b；如有 GPU，可选测试 qwen2.5:7b，但不阻塞默认方案。
- 本地把 `crawler/raw/` 和 `backend/data/chromadb/` 打包上传服务器
- 服务器上 `docker compose up -d --build`
- 域名解析 + Certbot 配 HTTPS Let's Encrypt
- 用外网及移动端验证 HTTPS、SSE、Wiki 链接；记录公网体验，并按第 8 周相同口径复测 CPU 性能。
- 跑 15 条端到端验收测试问题，截图记录
- 最终验收 checklist：功能验证 + 分层验证 + 性能指标
- 整理 README 和部署手册：启动、配置、索引恢复、更新回滚、已知限制。

### 本周交付物

- ✅ 公网可访问的 TerraGuide 实例
- ✅ HTTPS 正常，移动端可用
- 提交 15 问验收明细：核心要点覆盖率目标 ≥ 70%，附失败项、复测结果及是否影响发布的结论。
- ✅ README 部署文档

### 周末验收

留存公网地址或受限说明、证书检查与 15 问评分；复测 CPU 性能及 ≥ 5 路并发，GPU 端到端 ≤ 5 秒仅在具备 GPU 时实测。

### 风险预判

预留 1–2 天排查域名、证书及流式代理；若缺少公网条件，交付本地可复现演示并标明公网上线未验收。

---

## 附录：关键验收指标

| 指标 | 目标 | 验收时机 |
|------|------|----------|
| 爬虫抓取量 | ≥ 1500 个原版页面 | 第 2 周末 |
| 纯向量检索 Top-10 命中率 | 固定 10 条查询，记录实测基线，不设硬门槛 | 第 4 周末 |
| 混合检索 Top-5 命中率 | ≥ 80% | 第 4 周末 |
| RAG 端到端要点覆盖率 | ≥ 70% | 第 7 周末 |
| 纯 CPU 端到端响应 | ≤ 20 秒，首 token ≤ 10 秒 | 第 8 周末 |
| A/B 对比 B 组优势 | 固定 15 问；记录两组覆盖率、差值与失败案例，不更换题目 | 第 9 周末 |
| 公网功能 | HTTPS、来源链接、SSE、移动端可用；有条件时验收公网 | 第 13 周末 |
| 并发与 GPU（可选） | ≥ 5 路对话；仅有 GPU 时测 3B 端到端 ≤ 5 秒 | 第 13 周末 |

核心原则：Phase 1 的数据质量直接决定 Phase 2 的 RAG 效果。

如果第 4 周混合检索命中率达不到 80%，后面的工作应该暂停并先解决检索问题。
