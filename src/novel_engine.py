"""
小说生成引擎
基于热点元素，自我迭代，生成符合市场需求的小说章节
"""

import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

CHAPTERS_DIR = Path(__file__).parent.parent / "chapters"
MARKET_FILE = Path(__file__).parent.parent / "market_data" / "market_latest.json"
SKILLS_DIR = Path(__file__).parent.parent / "skills"

# 每章最少字数
MIN_CHARS_PER_CHAPTER = 4000

# 全书最少字数
MIN_TOTAL_CHARS = 10000


def load_market_data() -> dict:
    """加载市场热点数据"""
    if not MARKET_FILE.exists():
        return {
            "top_5": ["都市", "穿越", "玄幻", "甜宠", "悬疑"],
            "trends": ["系统流", "快节奏", "日常流"],
            "genres": ["都市言情", "玄幻修仙"]
        }
    with open(MARKET_FILE, encoding="utf-8") as f:
        return json.load(f)


def build_chapter_prompt(
    chapter_num: int,
    total_chapters: int,
    genre: str,
    themes: list[str],
    story_outline: dict,
    previous_summary: str,
    writing_tips: list[str],
) -> str:
    """构建章节写作提示词"""

    word_target = max(MIN_CHARS_PER_CHAPTER, 4500)

    prompt = f"""你是资深网络小说作家，精通{genre}类型小说创作。

【本章要求】
- 章节序号：第{chapter_num}章（共{total_chapters}章）
- 字数要求：不少于{word_target}字
- 写作风格：快节奏、高潮迭起、人物立体、对话生动
- 必须包含：冲突/转折/悬念，吸引读者追读

【市场热点参考】
- 当前热门类型：{', '.join(themes[:5])}
- 热门写法：{', '.join(story_outline.get('trends', [])[:5])}

【本书设定】
- 书名：《{story_outline.get('title', '未命名')}》
- 主线：{story_outline.get('main_plot', '待补充')}
- 核心冲突：{story_outline.get('core_conflict', '待补充')}
- 主角：{story_outline.get('protagonist', '待补充')}
- 背景：{story_outline.get('setting', '待补充')}

【前章概要】
{previous_summary}

【写作技巧】
{chr(10).join(f'- {tip}' for tip in writing_tips[:3])}

请开始创作第{chapter_num}章，要求：
1. 开篇直接切入剧情，不要写"章节名"
2. 章节内要有明确的冲突推进
3. 结尾留有悬念或钩子
4. 禁止水文、禁止凑字数
5. 中文写作，语言生动，符合网文读者习惯

请输出完整章节内容："""
    return prompt


def build_outline_prompt(market: dict) -> str:
    """构建大纲提示词"""
    hot_types = market.get("top_5", ["都市", "穿越", "玄幻"])
    trends = market.get("trends", ["系统流", "快节奏"])
    genres = market.get("genres", ["都市言情", "玄幻修仙"])

    prompt = f"""你是资深网文策划，精通市场需求和读者心理。

【当前市场热点】
热门类型：{', '.join(hot_types)}
热门写法：{', '.join(trends)}
热门题材：{', '.join(genres)}

【任务】
请设计一部小说的完整大纲，要求：
1. 题材要契合当前市场热点
2. 类型选择市场验证过的热门类型
3. 开篇要有强冲突/强悬念/强金手指
4. 前10章必须有明确的高潮点
5. 主角要有成长曲线和鲜明性格
6. 设定要有新意，避免老套

请输出JSON格式大纲：
{{
    "title": "书名（新颖有吸引力）",
    "genre": "题材类型",
    "setting": "世界观/背景设定",
    "protagonist": "主角人设（姓名+性格+背景+金手指）",
    "core_conflict": "核心冲突",
    "main_plot": "主线剧情概述",
    "chapters_plan": "各章节核心事件（至少5章，每章一句）",
    "selling_points": ["卖点1", "卖点2", "卖点3"],
    "target_readers": "目标读者群体",
    "word_count_target": "计划总字数"
}}"""
    return prompt


def count_chinese_chars(text: str) -> int:
    """统计中文字符数（不含标点空格）"""
    chars = re.findall(r'[\u4e00-\u9fff]', text)
    return len(chars)


def call_llm(prompt: str, system: Optional[str] = None) -> str:
    """调用 LLM 生成内容"""
    import os

    # 优先使用 MiniMax API（当前 Agent 所在平台）
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    model = os.environ.get("MINIMAX_MODEL", "MiniMax-Text-01")

    if not api_key:
        # 尝试使用 OpenAI
        api_key = os.environ.get("OPENAI_API_KEY", "")
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        # 使用 Nous/自有端点
        api_key = os.environ.get("NOUS_API_KEY", "")
        model = os.environ.get("NOUS_MODEL", "NousResearch/Hermes-3-Llama-3.1-8B")

    if not api_key:
        return generate_fallback_chapter(prompt)

    # 调用 MiniMax API
    if "minimax" in model.lower() or "MiniMax" in model:
        return call_minimax(prompt, system, api_key, model)

    return call_openai_compatible(prompt, system, api_key, model)


def call_minimax(prompt: str, system: Optional[str], api_key: str, model: str) -> str:
    """调用 MiniMax API"""
    import urllib.request
    import urllib.parse

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.85,
        "max_tokens": 8192,
    }

    req = urllib.request.Request(
        "https://api.minimax.chat/v1/text/chatcompletion_pro?GroupId="
        + os.environ.get("MINIMAX_GROUP_ID", ""),
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[LLM] MiniMax 调用失败: {e}")
        return ""


def call_openai_compatible(prompt: str, system: Optional[str], api_key: str, model: str) -> str:
    """调用 OpenAI 兼容 API"""
    import urllib.request

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # 检测 base URL
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.85,
        "max_tokens": 8192,
    }

    url = f"{base_url.rstrip('/')}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[LLM] OpenAI兼容调用失败: {e}")
        return ""


def generate_fallback_chapter(prompt: str) -> str:
    """无 API 时的占位章节生成（基于规则）"""
    # 这是一个简化版，实际部署时必须接入真实 LLM
    return f"""
【本章为自动生成占位内容】

由于未配置 LLM API，本章为占位内容。

要启用真实写作功能，请设置以下环境变量之一：
- MINIMAX_API_KEY + MINIMAX_GROUP_ID
- OPENAI_API_KEY + OPENAI_BASE_URL
- NOUS_API_KEY

当前热点关键词：{load_market_data().get('top_5', ['都市', '穿越'])}
"""


def write_outline_to_file(outline: dict, path: Path):
    """将大纲写入文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(outline, f, ensure_ascii=False, indent=2)


def generate_novel(outline: dict, market: dict, chapter_num: int, previous_summary: str) -> dict:
    """生成单章小说"""
    print(f"[生成] 开始生成第{chapter_num}章...")

    total_ch = max(10, chapter_num + 5)
    writing_tips = [
        "每800字设置一个小高潮，每2000字一个大悬念",
        "主角每章至少做一件有性格的事",
        "对话要推动剧情，不写废话对话",
        "描写简洁有力，避免过度环境描写",
    ]

    prompt = build_chapter_prompt(
        chapter_num=chapter_num,
        total_chapters=total_ch,
        genre=outline.get("genre", "都市言情"),
        themes=market.get("top_5", []),
        story_outline=outline,
        previous_summary=previous_summary,
        writing_tips=writing_tips,
    )

    content = call_llm(prompt)

    if not content or len(content) < 100:
        print(f"[生成] LLM 返回内容过短，使用占位内容")
        content = generate_fallback_chapter(prompt)

    char_count = count_chinese_chars(content)

    # 强制补字数（如果不够）
    if char_count < MIN_CHARS_PER_CHAPTER:
        shortfall = MIN_CHARS_PER_CHAPTER - char_count
        extension_prompt = f"""
前文内容字数不足{shortfall}字，请续写一段来扩充内容，续写要求：
- 延续当前剧情
- 不重复已有内容
- 自然过渡，不生硬
- 续写内容不少于{shortfall}字

前文：
{content[-1000:]}
"""
        extension = call_llm(extension_prompt)
        if extension and len(extension) > 50:
            content += "\n\n" + extension
            char_count = count_chinese_chars(content)

    print(f"[生成] 第{chapter_num}章完成，约 {char_count} 中文字符")

    return {
        "chapter_num": chapter_num,
        "content": content,
        "char_count": char_count,
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M"),
    }


def save_chapter(chapter_data: dict, story_id: str, chapter_num: int, base_dir: Path):
    """保存章节到文件"""
    story_dir = base_dir / story_id
    story_dir.mkdir(exist_ok=True)

    chapter_file = story_dir / f"chapter_{chapter_num:03d}.txt"
    with open(chapter_file, "w", encoding="utf-8") as f:
        f.write(f"第{chapter_num}章\n")
        f.write("=" * 40 + "\n\n")
        f.write(chapter_data["content"])

    meta_file = story_dir / f"chapter_{chapter_num:03d}_meta.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump({
            "chapter_num": chapter_num,
            "char_count": chapter_data["char_count"],
            "timestamp": chapter_data["timestamp"],
        }, f, ensure_ascii=False, indent=2)

    return chapter_file


def build_full_novel(story_id: str, base_dir: Path) -> Path:
    """将所有章节合并为完整小说"""
    story_dir = base_dir / story_id
    chapter_files = sorted(story_dir.glob("chapter_*.txt"))

    full_content = []
    meta = {"story_id": story_id, "chapters": [], "total_chars": 0}

    for cf in chapter_files:
        with open(cf, encoding="utf-8") as f:
            content = f.read()
        # 去掉元信息头部
        lines = content.split("\n")
        if "=" in content:
            sep_idx = next((i for i, l in enumerate(lines) if "=" in l), 0)
            content = "\n".join(lines[sep_idx + 1:])

        full_content.append(f"\n\n{'='*50}\n{cf.stem.replace('chapter_', '第').replace('_', '章')}\n{'='*50}\n\n")
        full_content.append(content)

        # 统计
        char_count = count_chinese_chars(content)
        meta["chapters"].append({
            "file": cf.name,
            "chars": char_count,
        })
        meta["total_chars"] += char_count

    # 写入全文
    full_file = story_dir / "full_novel.txt"
    with open(full_file, "w", encoding="utf-8") as f:
        f.write("\n".join(full_content))

    # 写入元数据
    meta_file = story_dir / "meta.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"[小说] 合并完成：{len(chapter_files)}章，共 {meta['total_chars']} 字")
    return full_file


def create_new_story(outline: dict, market: dict, story_id: str) -> dict:
    """创建新故事：生成第1章"""
    print(f"[故事] 创建新故事: {story_id}")
    story_dir = CHAPTERS_DIR / story_id
    story_dir.mkdir(exist_ok=True, parents=True)

    # 保存大纲
    write_outline_to_file(outline, story_dir / "outline.json")

    result = generate_novel(outline, market, 1, "【新书开篇，无前章】")
    save_chapter(result, story_id, 1, CHAPTERS_DIR)

    return {
        "story_id": story_id,
        "outline": outline,
        "current_chapter": 1,
        "status": "created",
    }


def update_story_chapter(story_id: str, outline: dict, market: dict, chapter_num: int) -> dict:
    """更新指定章节"""
    story_dir = CHAPTERS_DIR / story_id

    # 获取前章概要
    prev_summary = ""
    if chapter_num > 1:
        prev_file = story_dir / f"chapter_{chapter_num-1:03d}.txt"
        if prev_file.exists():
            with open(prev_file, encoding="utf-8") as f:
                prev_text = f.read()
            # 提取最后500字作为前章概要
            prev_summary = prev_text[-800:] if len(prev_text) > 800 else prev_text

    result = generate_novel(outline, market, chapter_num, prev_summary)
    save_chapter(result, story_id, chapter_num, CHAPTERS_DIR)

    return result


def get_story_progress(story_id: str) -> dict:
    """获取故事进度"""
    story_dir = CHAPTERS_DIR / story_id
    if not story_dir.exists():
        return {"chapters": 0, "exists": False}

    chapters = sorted(story_dir.glob("chapter_*.txt"))
    meta_path = story_dir / "meta.json"

    meta = {}
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

    outline_path = story_dir / "outline.json"
    outline = {}
    if outline_path.exists():
        with open(outline_path, encoding="utf-8") as f:
            outline = json.load(f)

    return {
        "chapters": len(chapters),
        "exists": True,
        "meta": meta,
        "outline": outline,
        "story_id": story_id,
    }
