# TerraGuide —— 泰拉瑞亚 AI 攻略搜索 项目计划

> 一个基于 Wiki 数据 + 本地大模型 RAG 的泰拉瑞亚自然语言攻略助手
> 
> **范围限定：仅支持 1.4 原版（Journey's End）内容，不含 TModLoader 模组**

---

## 一、项目概述

TerraGuide 解决的核心痛点：**现有攻略只能按词条（BOSS、装备、物品）搜索，玩家无法直接用自然语言询问自己游戏进程中的决策问题。**

典型用户查询示例（全是原版 1.4 场景）：
- "我刚打完肉山，玩召唤师，接下来优先做什么装备？"
- "专家模式机械骷髅王怎么打？我是战士，有钛金套。"
- "新三王之前，法师最好的武器是什么？"

这些问题需要 AI 理解玩家的**游戏进度**、**职业**、**难度模式**和**装备预算**，然后从 Wiki 中检索相关片段并组合成有针对性的建议。

### 原版职业（仅这四个）
- 战士（Melee）
- 游侠（Ranged）
- 法师（Magic）
- 召唤师（Summoner）

### 项目亮点（面试/博客素材）
- **差异化的游戏状态解析**：把玩家自然语言映射到"可用内容集合"，而不是简单排除
- **RAG 基线对比**：实测"有无检索对答案质量的影响"，用数据证明 RAG 价值
- **纯 CPU 可跑**：默认 3B 模型在消费级 CPU 上约 8 tok/s，20 秒内出首 token

---

## 二、技术架构

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   前端 Web    │────▶│  FastAPI 后端      │────▶│  Ollama 本地 LLM│
│  React + Vite │◀────│  (RAG 编排 + API)  │◀────│  (qwen2.5:3b)   │
└──────────────┘     └────────┬─────────┘     └─────────────────┘
                               │
                      ┌────────┴─────────┐
                      │   向量数据库      │
                      │  ChromaDB        │
                      │  (Wiki 内容切片)  │
                      └──────────────────┘
                               ▲
                      ┌────────┴─────────┐
                      │  Wiki 爬虫        │
                      │  MediaWiki API    │
                      │  (terraria.wiki.gg)│
                      └──────────────────┘
```

### 技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| **前端** | React + Vite + TailwindCSS | 轻量快速，组件生态丰富 |
| **后端** | Python FastAPI | 与 AI/RAG 生态无缝衔接，异步高性能 |
| **AI 编排** | Ollama | 本地部署，直接调 `/api/chat`，LangChain 可选（0.3.x 后 Memory 模块已迁移，多轮对话用原生 messages 列表即可，不依赖旧 API） |
| **向量库** | ChromaDB | 轻量嵌入式，无需独立服务 |
| **Embedding** | bge-m3（索引用）+ all-MiniLM-L6-v2（查询用，45MB） | bge-m3 做一次性索引构建，all-MiniLM-L6-v2 做轻量查询编码，后端不需要常驻 bge-m3 |
| **LLM（默认）** | qwen2.5:3b | 纯 CPU 下约 8 tok/s，prefill 延迟低；有 RAG 检索片段约束时，3B 退化不明显 |
| **LLM（GPU 可选）** | qwen2.5:7b | 有 NVIDIA GPU 时切换，指令遵循更强 |
| **爬虫** | requests + MediaWiki API + BeautifulSoup | terraria.wiki.gg 有完整 `/api.php`，无需渲染 JS；Playwright 作为 API 不完整时的兜底 |
| **部署** | Docker Compose + 云服务器 | 一键部署，Nginx 反代 HTTPS |

---

## 三、Wiki 数据范围（原版 1.4 Journey's End）

爬虫只抓取以下核心分类页面：

| 分类 | 预估页面数 | 说明 |
|------|-----------|------|
| Bosses | ~50 | 所有原版 Boss（含事件 Boss） |
| Weapons | ~400 | 四职业全武器 |
| Armor | ~100 | 全护甲套装 |
| Accessories | ~200 | 全饰品 |
| Items | ~1500 | 消耗品、材料、方块等 |
| NPCs | ~30 | 原版 NPC 及其商店 |
| Game mechanics | ~80 | 游戏机制（战斗、挖矿、建造、农场等） |
| Events | ~20 | 血月、日食、南瓜月、霜月等 |
| Progression guides | ~30 | 各类进度指南 |

**排除内容**：Mods 分类、Modded NPC、Calamity/Thorium 等模组页面。

---

## 四、项目结构

```
Terraguide/
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── components/          # UI 组件
│   │   │   ├── ChatBox.jsx      # 主对话区域
│   │   │   ├── Message.jsx      # 消息气泡（用户/AI）
│   │   │   ├── SourceCard.jsx   # Wiki 来源卡片
│   │   │   ├── GameContext.jsx  # 游戏状态快捷设置面板
│   │   │   └── Sidebar.jsx      # 历史对话 / 新建
│   │   ├── api/                 # 后端 API 封装
│   │   ├── hooks/               # 自定义 React hooks
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
│
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── api/
│   │   │   ├── chat.py          # POST /api/chat, /api/chat/stream
│   │   │   └── health.py        # GET /api/health, /api/sources
│   │   ├── core/
│   │   │   ├── rag.py           # RAG 编排：检索 + 重排 + 生成
│   │   │   ├── prompts.py       # System Prompt 模板
│   │   │   ├── game_state.py    # 游戏状态解析 + 进度映射表
│   │   │   └── progression.py   # 进度 → 允许的 Wiki 分类/标签映射表
│   │   ├── services/
│   │   │   ├── llm.py           # Ollama 客户端封装
│   │   │   └── vectorstore.py   # ChromaDB 操作 + 混合检索
│   │   └── config.py            # 配置常量
│   ├── data/                    # ChromaDB 持久化目录
│   ├── logs/
│   ├── requirements.txt
│   └── Dockerfile
│
├── crawler/                     # Wiki 爬虫（独立脚本，一次性运行）
│   ├── scrape.py                # MediaWiki API 抓取入口（requests）
│   ├── parser.py                # API 返回内容 → Markdown + 元数据（BeautifulSoup 清洗）
│   ├── chunker.py               # 文档切片
│   ├── embed.py                 # bge-m3 一次性算完 embedding（索引用）
│   ├── ingest.py                # 写入 ChromaDB
│   ├── categories.yaml          # 要抓取的原版分类白名单
│   └── raw/                     # 抓取的原始数据（.md 文件）
│
├── eval/                        # RAG 评估（面试/博客素材）
│   ├── baseline.py              # 无 RAG 纯 LLM 基线
│   ├── test_cases.json          # 15 条测试问题 + 期望要点
│   └── compare.py               # 有 RAG vs 无 RAG 答案质量对比
│
├── docker-compose.yml           # 一键部署
└── .gitignore
```

---

## 五、实施步骤

### Phase 1：Wiki 数据采集与 RAG 底座

**Step 1 — 爬虫框架（MediaWiki API + requests）**
- 用 `requests` 调用 terraria.wiki.gg 的 MediaWiki API（`action=query`、`action=parse`）
  - 列出分类成员：`/api.php?action=query&list=categorymembers&cmtitle=Category:Bosses&cmlimit=500`
  - 获取页面正文：`/api.php?action=parse&page={title}&prop=text`
- 配置：User-Agent（注明用途 + 联系方式）、请求间隔 1 秒、失败重试 3 次
- BeautifulSoup 仅用于清洗 API 返回的 HTML 片段（Infobox、合成配方表格等）
- Playwright 作为**兜底方案**：API 对某些页面返回内容不完整（如动态展开的折叠面板）时，才 fallback 到 Playwright 渲染
- 按 `categories.yaml` 白名单只爬原版分类，跳过 Mods 相关页面
- 输出到 `crawler/raw/{category}/{page_title}.md`

> **为什么不用 Playwright 做默认？** terraria.wiki.gg 所有内容都是服务端渲染的 MediaWiki 页面，`action=parse` API 直接返回完整 HTML，不需要浏览器。Playwright 每个页面启动浏览器实例，内存成本是 requests 的 100 倍+，爬 2000 个页面的时间从十几分钟变成几小时。

**Step 2 — 内容清洗（BeautifulSoup）**
- 解析 API 返回的 HTML，提取 `<div class="mw-parser-output">` 正文
- 移除：导航框、编辑链接、广告、Mod 模板、折叠框默认内容
- 解析 Infobox（BOSS 属性、物品属性）为结构化键值对
- 解析合成配方（Crafting Station + 材料 → 产物）为结构化表格
- 为每条记录附加元数据：`{title, category, url, aliases, is_hardmode, boss_stage}`
- **`is_hardmode` 标记**：根据 Wiki 分类标签（`Hardmode-only content` / `Pre-Hardmode content`）自动标注，后续进度映射直接用

**Step 3 — 切片与向量化（一次性完成）**
- 切片策略：按二级标题切分，每个 chunk 500-800 tokens，相邻 chunk overlap 100 tokens
- 用 `sentence-transformers` 的 **bge-m3** 生成 embedding（仅在这个阶段运行，一次性算完所有 chunk）
- **写入两个字段到 ChromaDB**：
  - 索引向量：bge-m3 embedding（高质量，用于精确相似度）
  - 查询向量预存：同时用 **all-MiniLM-L6-v2（45MB）** 再算一份，或者把 bge-m3 的查询编码也在这个阶段预处理好
- 存入 ChromaDB，collection 名 `terraria_wiki_v1`
- **后端服务不需要常驻 bge-m3 模型**，查询时直接读预存的向量即可（或用 MiniLM 做轻量查询编码）

**Step 4 — 数据质量验证（分层指标）**

| 检索方式 | 验证指标 | 目标 |
|----------|----------|------|
| 纯向量检索 | Top-10 中包含正确答案页面的比例 | 先测基线，**不设硬指标**（专有名词密集场景纯向量大概率 < 60%） |
| 向量 + 关键词混合检索 | Top-5 中包含正确答案页面的比例 | **≥ 80%** |
| 最终 RAG 端到端 | 15 条测试问题中，答案核心要点被覆盖的比例 | **≥ 70%** |

- 先跑纯向量基线，拿到数字面试时可以说"我们实测了纯向量命中率只有 XX%，所以必须做混合检索"
- 示例测试查询："Guide Voodoo Doll"、"Spider Armor set bonus"、"机械三王召唤物"、"Zenith"

---

### Phase 2：后端 RAG 引擎

**Step 5 — FastAPI 骨架**
- 项目初始化：依赖（fastapi, uvicorn, chromadb, httpx, sentence-transformers[轻量版]）、路由、CORS 中间件
- **关于 LangChain**：LangChain 0.3.x 之后 `ConversationSummaryBufferMemory` 等 Memory 模块已迁移。多轮对话直接用原生 messages 列表（保留最近 3 轮，超过截断），不用 Memory 类。RAG 编排自己写（检索 → 拼 Prompt → 调 Ollama），不用 LangChain 的 Chain 抽象——对 demo 来说自己写 50 行比引一个大依赖更可控
- Ollama 健康检查：启动时探测 Ollama 是否运行、qwen2.5:3b 是否已拉取
- **默认模型 qwen2.5:3b，GPU 环境下可通过环境变量切换到 qwen2.5:7b**
- 如果 Ollama 未运行，启动脚本给出明确提示

**Step 6 — 混合检索服务**
- **向量检索**：用户问题 → 轻量 embedding（all-MiniLM-L6-v2，45MB）→ ChromaDB cosine similarity → Top 50
- **关键词检索**：用户输入提取专有名词（武器名、BOSS 名、物品名、中英文别名）→ 精确匹配元数据 title/aliases 字段 → 加权提升（+0.3）
- **重排序**：对合并后的候选片段，用 LLM（可选，成本高）或 CrossEncoder（可选）做 rerank → 取 Top 10
- 最终返回格式：`[{content, source_url, score, metadata: {title, category, is_hardmode, boss_stage}}]`

**Step 7 — 游戏状态解析 + 进度映射表（差异化核心）**

#### 7.1 状态解析

从用户自然语言中提取：

| 字段 | 可选值 | 提取方式 |
|------|--------|----------|
| **游戏进度** | `pre_hardmode` / `post_wall_of_flesh` / `post_mech_bosses` / `post_plantera` / `post_golem` / `post_cultist` / `post_moon_lord` | 关键词匹配 + 时间排序 BOSS 关联 |
| **职业** | 战士 / 游侠 / 法师 / 召唤师 | 关键词匹配 + Wiki 分类交叉验证 |
| **难度** | 普通 / 专家 / 大师 | 关键词匹配 |
| **预算/偏好** | fast / normal / farm | "不想刷太久" → fast，"farm" → farm |

> 实现策略：先用纯规则（关键词词典 + 正则）实现，覆盖 80% 场景。

#### 7.2 进度 → 允许集合映射表

**不用排除规则，用允许集合。** 每个进度阶段对应一张"允许的 Wiki 分类/标签"白名单，检索时只在这些范围内搜。

| 进度阶段 | 允许的 Wiki 分类 / 元数据标签 |
|----------|-------------------------------|
| `pre_hardmode` | `is_hardmode=false`，Bosses 中排除机械三王/世纪之花/石巨人/邪教徒/月总，Items 中排除硬模式掉落 |
| `post_wall_of_flesh` | `is_hardmode=true`，Bosses 中排除机械三王后的内容 |
| `post_mech_bosses` | `is_hardmode=true`，排除世纪之花后的 BOSS 和物品 |
| `post_plantera` | 排除石巨人后的 BOSS 和物品 |
| `post_golem` | 排除邪教徒和四柱 |
| `post_cultist` | 包含四柱，排除月总掉落 |
| `post_moon_lord` | 全部内容 |

> ChromaDB 查询时用 `where={"$or": [允许的 category 列表], "is_hardmode": 允许值}` 过滤。
> 这个映射表就是一个 Python 字典，面试时可以展示"我们的规则引擎就是一张表"。

**Step 8 — Prompt 工程**

```
System Prompt:
你是一位资深泰拉瑞亚 1.4 原版攻略顾问。你的知识库来自 terraria.wiki.gg。
用户会用自然语言问关于游戏攻略的问题，你需要：
1. 先理解用户的游戏进度、职业、难度和预算偏好
2. 从提供的 Wiki 资料中检索相关信息
3. 给出分点的、有优先级的建议
4. 每条建议标注"为什么推荐"（掉落来源、制作成本、稀有度、与游戏进度的匹配度）
5. 如果资料中没有答案，坦诚说明，不要编造
6. 回答末尾以"## 参考来源"为标题列出参考的 Wiki 页面标题

游戏进度时间线（原版 1.4，已修正）：
肉前（含新三王：克苏鲁之脑 / 世界吞噬者 / 骷髅王）
→ 血肉墙 Wall of Flesh（击杀后进入硬模式）
→ 硬模式早期（血肉墙后 → 机械三王前）
→ 机械三王（机械骷髅王 / 毁灭者 / 双子魔眼）
→ 世纪之花 Plantera
→ 石巨人 Golem
→ 地牢邪教徒 Lunatic Cultist
→ 四柱（Solar / Nebula / Stardust / Vortex）
→ 月之领主 Moon Lord

当前游戏状态（用户提到的）：
{game_state_json}
```

**Step 9 — API 接口**

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/chat` | 完整对话（非流式），返回 `{answer, sources: [...]}` |
| POST | `/api/chat/stream` | SSE 流式输出，逐步推送 token + 最终 sources |
| GET | `/api/health` | 健康检查（后端、Ollama、ChromaDB 状态） |
| GET | `/api/sources` | 返回索引统计（页面数、分类分布、数据大小） |

### Phase 2.5（附加）：RAG 基线对比

> 面试/博客的好素材。用数据证明"为什么需要 RAG"。

**跑 15 条测试问题，两组对照：**
- **A 组（无 RAG）**：只把用户问题发给 LLM，让它凭参数记忆回答
- **B 组（有 RAG）**：按完整 RAG 流程回答

**评估维度：**

| 评估维度 | A 组（无 RAG）预期 | B 组（有 RAG）预期 |
|----------|-------------------|-------------------|
| 核心要点覆盖率 | 可能 < 50%（LLM 知识可能缺失或过时） | ≥ 70%（检索片段强制约束） |
| 物品/BOSS 名称准确性 | 可能出现编造（如 Calamity 物品） | 必须来自 Wiki |
| 进度匹配度 | 可能把肉后装备推荐给肉前玩家 | 进度映射表约束 |
| 引用来源 | 无 | 有，可追溯 |

**输出物**：一张对比表 + 3-5 个具体例子（A 组回答 vs B 组回答），写成博客或者面试时直接展示。

---

### Phase 3：前端界面

**Step 10 — 项目初始化**
- `npm create vite@latest frontend -- --template react`
- 安装 tailwindcss、@tailwindcss/typography
- 配置 Vite proxy：`/api` → `http://localhost:8000`

**Step 11 — 组件开发**

| 组件 | 职责 |
|------|------|
| `ChatBox` | 滚动消息列表 + 输入框 |
| `Message` | 用户消息（右对齐）/ AI 消息（左对齐 + Markdown 渲染） |
| `SourceCard` | AI 回答底部的 Wiki 来源卡片：标题 + URL + 点击跳转 |
| `GameContext` | 可选面板：职业下拉、进度下拉、难度下拉、预算滑块 → 帮助用户设定游戏状态 |
| `Sidebar` | 左侧边栏："新建对话"按钮 + 历史对话列表（localStorage 持久化） |

**Step 12 — 体验优化**
- SSE 流式输出：打字机效果逐步渲染 AI 回答
- Loading 状态：AI 思考中显示"分析游戏上下文..." + "检索 Wiki..." + "整理答案..." 三段 loading
- Quick Prompts：3-4 个常见问题快捷按钮（"刚打完肉山该做什么？"）
- 暗色/亮色主题切换
- 移动端响应式布局

---

### Phase 4：部署上线

**Step 13 — Docker Compose**

```yaml
services:
  frontend:    # nginx 托管静态文件 + /api 反代
  backend:     # uvicorn app.main:app --host 0.0.0.0
  ollama:      # ollama serve (可选映射 GPU)
```

前端 Nginx 配置要点：
- `/` → 静态文件
- `/api/` → proxy_pass 到 backend:8000（注意 SSE 要关掉 proxy_buffering）
- 启用 gzip

**Step 14 — 服务器准备**
- **最低配置（纯 CPU）**：4 核 CPU + 8GB RAM（3B 模型 CPU 推理 ~8 tok/s，prefill 延迟 ~5-10s）
- **推荐配置（GPU）**：NVIDIA GPU + 16GB RAM（3B/7B 模型 GPU 推理 ~30-50 tok/s）
- 安装 Docker + Docker Compose + NVIDIA Container Toolkit（如有 GPU）
- 域名备案 + DNS 解析

**Step 15 — 上线流程**
1. 服务器上 `ollama pull qwen2.5:3b`（GPU 可额外 `ollama pull qwen2.5:7b`）
2. 本地把爬好的 `crawler/raw/` 和向量索引（`backend/data/`）打包上传到服务器
3. `docker compose up -d --build`
4. Certbot 配置 Let's Encrypt HTTPS
5. 公网访问测试

---

## 六、关键设计决策

### 6.1 为什么默认用 qwen2.5:3b 而不是 7B？
- CPU 推理 7B 的 prefill 延迟约 20-30 秒，直接破坏"20 秒出首 token"目标
- 3B 在 CPU 上约 8 tok/s，prefill 延迟约 5-10 秒，首 token 可在 15 秒内到达
- RAG 场景有检索片段作为硬约束，"基于给定资料回答"的任务上 3B vs 7B 的退化远小于通用对话场景
- 7B 列为 GPU 可选方案，通过环境变量切换
- **面试时可以说**："我们先用 3B 跑通 demo，确保 CPU 机器体验可接受，有 GPU 再升级 7B"——体现务实

### 6.2 爬虫为什么用 MediaWiki API 而不是 Playwright？
- terraria.wiki.gg 的 MediaWiki API 完整返回所有页面正文，不需要浏览器渲染
- requests + BeautifulSoup 的资源消耗是 Playwright 的 1/100，爬 2000 页从几小时变成十几分钟
- Playwright 作为兜底：API 不完整的极少数页面才 fallback

### 6.3 进度映射用"允许集合"而非"排除规则"

早期想法是"排除肉后物品"，但实际上玩家问"刚打完肉山"时，需要的是**肉后初级**装备，不是排除所有肉后物品。

正确做法：维护一张进度 → 允许的 Wiki 分类/标签的**映射表**。规则引擎查表，检索时用 ChromaDB 的 `where` 条件直接过滤。

```python
PROGRESSION_ALLOWLIST = {
    "post_wall_of_flesh": {
        "hardmode": True,
        "exclude_bosses_after": "post_mech_bosses",
        "allowed_categories": ["Weapons", "Armor", "Accessories", "Bosses"],
    },
    "pre_hardmode": {
        "hardmode": False,
        "allowed_categories": ["Weapons", "Armor", "Accessories", "Bosses"],
    },
    # ...
}
```

这比写一堆容易出错的 if/else 排除条件可维护得多，面试时可以展示。

### 6.4 Embedding 为什么不在后端常驻？
- bge-m3 模型 ~2GB，后端 FastAPI + ChromaDB + Ollama 已经占内存
- 4 核 8GB 机器上，bge-m3 + Ollama 3B + uvicorn 同时跑可能 OOM
- **解决方案**：索引用 bge-m3 一次性算完，存进 ChromaDB；查询时用轻量 all-MiniLM-L6-v2（45MB）或者直接把 bge-m3 查询编码也在索引阶段预处理好
- Ollama 本身也提供 embedding API（`/api/embeddings`），可以考虑让 Ollama 负责 embedding，后端只调接口

### 6.5 混合检索（向量 + 关键词）
- 向量检索擅长语义："召唤师肉后起步" ≈ "summoner early hardmode"
- 关键词检索擅长专有名词："Zenith"、"Terra Blade"、"Plantera" 这类名字在 embedding 空间里不一定比其他句子更近，必须精准命中
- 两路结果合并后按分数排序取 Top 10

### 6.6 多轮对话
- 直接保留最近 3 轮 messages 到 Ollama 请求里，不用 Memory 类
- LangChain 0.3.x 后 Memory 模块已迁移，照教程写旧 API 会 import 报错
- 超过 3 轮时截断，对攻略问答场景已经够用

---

## 七、风险与应对

| 风险 | 应对方案 |
|------|----------|
| **Wiki API 限流或反爬** | 降低频率（1秒/请求），多 User-Agent，API 失败时 fallback XML dump |
| **纯向量检索命中率不够** | 已预期，通过混合检索（+关键词）补强；单独测纯向量基线拿数字 |
| **本地 LLM 回答质量不够好** | 1) 3B + RAG 检索片段约束，退化可控；2) 有 GPU 切换 7B；3) 精心调 System Prompt |
| **后端内存不足** | Embedding 不常驻后端；索引用 bge-m3 一次性算完；查询用 MiniLM 或 Ollama API |
| **服务器 GPU 不够快** | 1) 纯 CPU 跑 3B（~8 tok/s）；2) 流式输出掩盖延迟；3) 租用 AutoDL 等 GPU 实例（按小时付费） |
| **Wiki 内容更新** | 每月重新跑一次 ingest.py，增量更新 ChromaDB |
| **公网被滥用** | Nginx 层 IP 限流（100 req/min/IP），后端加简单 token 鉴权 |
| **LangChain API 变化** | 干脆不用 LangChain，RAG 编排自己写 50 行代码，可控不依赖 |

---

## 八、验证清单

### 分层验证（核心）

| 阶段 | 验证项 | 方式 | 目标 |
|------|--------|------|------|
| Phase 1 | 爬虫抓取量 | 统计 .md 文件数 | ≥ 1500 个原版页面 |
| Phase 1 | 纯向量检索基线 | 10 条查询手动评估 Top-10 召回 | 先测数字，**不设硬指标** |
| Phase 1 | 混合检索命中率 | 20 条查询 Top-5 包含正确页面 | **≥ 80%** |
| Phase 2 | RAG 端到端 | 15 条测试问题核心要点覆盖率 | **≥ 70%** |
| Phase 2.5 | 有 RAG vs 无 RAG 对比 | A/B 两组回答质量评分 | B 组要点覆盖率显著优于 A 组 |

### 功能验证
- [ ] AI 回答必附 Wiki 来源 URL
- [ ] SSE 流式输出正常
- [ ] Docker Compose 一键启动
- [ ] 健康检查接口返回 Ollama + ChromaDB 状态

### 性能指标
- 纯 CPU（3B）：端到端响应 ≤ 20 秒，首 token ≤ 10 秒
- GPU（3B）：端到端响应 ≤ 5 秒
- 并发 ≥ 5 路对话

---

## 九、实施优先级总结

```
[Phase 1] 数据底座（不可跳过）
  └─ MediaWiki API 爬虫 → BeautifulSoup 清洗 → 切片 → bge-m3 embedding（一次性）→ ChromaDB
  └─ 跑纯向量检索基线（拿到一个数字）
  └─ 实现混合检索，命中率 ≥ 80%

[Phase 2] 后端引擎（不可跳过）
  └─ FastAPI 骨架 → Ollama 客户端 → ChromaDB 混合检索（where 条件用进度映射表）
  └─ 游戏状态解析 → 进度→允许集合映射表 → Prompt 模板
  └─ API（/chat, /chat/stream, /health, /sources）

[Phase 2.5] RAG 基线对比（面试/博客素材）
  └─ 写无 RAG 纯 LLM 脚本 → 跑 15 条测试问题 → 与有 RAG 结果对比 → 输出对比表

[Phase 3] 前端界面（不可跳过）
  └─ React 骨架 → ChatBox → SourceCard → GameContext → 体验优化

[Phase 4] 部署上线
  └─ Docker Compose → 服务器 → HTTPS → 公网验证
```

**核心风险点**：Phase 1 的爬虫质量 + 混合检索命中率。需要先把这两件事做好再往后推。
