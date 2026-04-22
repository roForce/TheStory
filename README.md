# TheStory

> 🤖 AI 全自动小说创作引擎 —— 每日扫描市场热点，每 10 分钟更新一章

## 项目概述

TheStory 是一个 AI 驱动的全自动小说创作系统，每日抓取全网热门元素（百度热搜、微博、知乎、小红书、网文平台），结合市场趋势自动生成并迭代小说内容。

## 核心功能

- 🔍 **每日市场扫描**：抓取全网小说热门元素（类型、题材、金手指、写法）
- 📖 **自动章节生成**：每 10 分钟生成/更新一章（不少于 4000 字）
- 🔄 **全量覆盖更新**：每次更新覆盖所有已有章节，确保内容一致性
- 🛠️ **Skill 自动迭代**：每日从 GitHub Trending 抓取最新小说写作技巧并安装
- 📤 **GitHub 同步**：每次更新自动推送，保持远程仓库最新

## 目录结构

```
TheStory/
├── src/
│   ├── orchestrator.py     # 主调度器
│   ├── market_scanner.py   # 市场热点扫描
│   ├── novel_engine.py     # 小说生成引擎
│   └── skill_updater.py    # Skill 自动更新
├── chapters/               # 章节存储
├── market_data/            # 市场数据
├── skills/                 # 写作技能库
├── logs/                   # 运行日志
└── README.md
```

## 运行模式

```bash
# 初始化（创建故事 + 生成第1章）
python src/orchestrator.py init

# 更新（生成下一章）
python src/orchestrator.py update

# 扫描市场
python src/orchestrator.py scan
```

## 环境变量

- `MINIMAX_API_KEY` + `MINIMAX_GROUP_ID`：MiniMax API
- `OPENAI_API_KEY` + `OPENAI_BASE_URL`：OpenAI 兼容 API
- `NOUS_API_KEY`：Nous API
- `GITHUB_TOKEN`：GitHub API（自动从 `gh auth` 获取）

## 自动调度

- **每 10 分钟**：生成/更新一章
- **每天**：扫描市场热点 + 更新写作 skills

## 写作流程

1. 每日扫描市场热点 → 生成契合市场需求的小说大纲
2. 生成第1章并保存
3. 每 10 分钟更新新章节
4. 每次更新覆盖所有章节为完整小说文件
5. 自动推送到 GitHub
6. Skill 系统每日迭代最新写作技巧
