"""
小说生成引擎
基于热点元素，自我迭代，生成符合市场需求的小说章节
使用 MiniMax M2.7 API（从 auth.json 读取密钥）
"""

import json
import re
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

CHAPTERS_DIR = Path(__file__).parent.parent / "chapters"
MARKET_FILE = Path(__file__).parent.parent / "market_data" / "market_latest.json"
SKILLS_DIR = Path(__file__).parent.parent / "skills"
MIN_CHARS_PER_CHAPTER = 4000
MAX_TOKENS_PER_CALL = 2000  # MiniMax M2.7 每次最多输出 token 数


def _load_minimax_credentials() -> tuple[str, str]:
    """从 auth.json 读取 MiniMax CN 凭证"""
    auth_path = Path.home() / ".hermes" / "auth.json"
    with open(auth_path, encoding="utf-8") as f:
        data = json.load(f)
    creds = data["credential_pool"]["minimax-cn"][0]
    return creds["access_token"], creds["base_url"]


def call_minimax(prompt: str, system: Optional[str] = None, max_tokens: int = 1800) -> str:
    """调用 MiniMax M2.7（Anthropic 兼容格式），返回文本"""
    key, base_url = _load_minimax_credentials()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "MiniMax-M2.7",
        "messages": messages,
        "max_tokens": max_tokens,
    }

    curl_cmd = [
        "curl", "-s", "--max-time", "150",
        "-X", "POST",
        f"{base_url}/v1/messages",
        "-H", f"Authorization: Bearer {key}",
        "-H", "Content-Type: application/json",
        "-H", "anthropic-version: 2023-06-01",
        "-d", json.dumps(payload),
    ]

    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=160)
        if result.returncode != 0:
            print(f"[LLM] curl failed: {result.stderr[:100]}")
            return ""
        resp = json.loads(result.stdout)
        content = resp.get("content", [])
        for block in content:
            if block.get("type") == "text":
                return block["text"]
        return ""
    except subprocess.TimeoutExpired:
        print("[LLM] MiniMax 调用超时")
        return ""
    except Exception as e:
        print(f"[LLM] MiniMax 调用失败: {e}")
        return ""


def generate_long_text(prompt: str, system: Optional[str] = None, min_chars: int = 4000) -> str:
    """
    尝试单次高 token 生成（3000 tokens ≈ 5000+ 中文字，约70s）
    若字数不够，再补一段续写
    """
    target_chars = max(min_chars, 4200)

    # 第一次：单次高token生成（减少调用次数）
    # MiniMax M2.7 内部限制约 1800-2200 tokens 输出，3000 可覆盖 4000+ 中文
    text1 = call_minimax(prompt, system, max_tokens=3000)
    if text1 and len(text1.strip()) > 50:
        char_count = sum(1 for c in text1 if '\u4e00' <= c <= '\u9fff')
        print(f"[LLM] 第1段: {char_count} 字")

        if char_count >= target_chars:
            return text1

        # 字数不够，续写
        continuation_prompt = f"""前文内容（约{char_count}字），请续写来达到约{target_chars}字。
要求：
- 自然衔接上文
- 不重复已有内容
- 保持节奏紧凑
- 继续推进剧情

前文末尾（最后200字）：
{text1[-200:]}

请续写："""
        text2 = call_minimax(continuation_prompt, system, max_tokens=1800)
        if text2 and len(text2.strip()) > 50:
            char2 = sum(1 for c in text2 if '\u4e00' <= c <= '\u9fff')
            print(f"[LLM] 第2段: {char2} 字")
            return text1 + "\n\n" + text2
        return text1

    return ""


def count_chinese_chars(text: str) -> int:
    """统计中文字符数（不含标点空格）"""
    return len(re.findall(r'[\u4e00-\u9fff]', text))


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
) -> tuple[str, str]:
    """构建章节写作提示词，返回 (system, prompt)"""
    word_target = max(MIN_CHARS_PER_CHAPTER, 4500)

    system = f"""你是资深网络小说作家，精通{genre}类型小说创作。
写作要求：
- 每800字设置一个小高潮，每2000字一个大悬念
- 主角每章至少做一件有性格的事
- 对话要推动剧情，不写废话对话
- 描写简洁有力，避免过度环境描写
- 章节字数不少于{word_target}字
- 禁止水文、禁止凑字数
- 中文写作，语言生动，符合网文读者习惯"""

    prompt = f"""【当前市场热点参考】
热门类型：{', '.join(themes[:5])}
热门写法：{', '.join(story_outline.get('trends', [])[:5])}

【本书设定】
- 书名：{story_outline.get('title', '未命名')}
- 主线：{story_outline.get('main_plot', '待补充')}
- 核心冲突：{story_outline.get('core_conflict', '待补充')}
- 主角：{story_outline.get('protagonist', '待补充')}
- 背景：{story_outline.get('setting', '待补充')}

【前章概要】
{previous_summary}

【写作技巧】
{chr(10).join(f'- {tip}' for tip in writing_tips[:3])}

请创作第{chapter_num}章，要求：
1. 开篇直接切入剧情，不要写"章节名"
2. 章节内要有明确的冲突推进
3. 结尾留有悬念或钩子，吸引读者追读
4. 不少于{word_target}字，节奏紧凑

请输出完整第{chapter_num}章内容："""
    return system, prompt


def build_outline_prompt(market: dict) -> tuple[str, str]:
    """构建大纲提示词"""
    hot_types = market.get("top_5", ["都市", "穿越", "玄幻"])
    trends = market.get("trends", ["系统流", "快节奏"])
    genres = market.get("genres", ["都市言情", "玄幻修仙"])

    system = "你是一个资深网文策划专家，精通市场需求和读者心理，只输出JSON格式。"

    prompt = f"""当前市场热点：
热门类型：{', '.join(hot_types)}
热门写法：{', '.join(trends)}
热门题材：{', '.join(genres)}

请设计一部小说的完整大纲，要求：
1. 题材契合当前市场热点
2. 开篇要有强冲突/强悬念/强金手指
3. 前10章必须有明确的高潮点
4. 主角要有成长曲线和鲜明性格
5. 设定要有新意，避免老套

输出严格JSON格式（不要有任何其他内容）：
{{
    "title": "书名（新颖有吸引力）",
    "genre": "题材类型",
    "setting": "世界观/背景设定",
    "protagonist": "主角人设",
    "core_conflict": "核心冲突",
    "main_plot": "主线剧情概述",
    "selling_points": ["卖点1", "卖点2", "卖点3"],
    "target_readers": "目标读者群体"
}}"""
    return system, prompt


def parse_outline(text: str) -> dict:
    """从 LLM 输出中解析 JSON 大纲"""
    text = text.strip()
    # 尝试提取 ```json ... ``` 或 ``` ... ```
    import re
    m = re.search(r'```(?:json)?\s*([\s\S]+?)```', text)
    if m:
        text = m.group(1)
    else:
        # 尝试找 { ... }
        m = re.search(r'\{[\s\S]+\}', text)
        if m:
            text = m.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"[大纲] JSON解析失败: {text[:200]}")
        return None


def generate_outline(market: dict) -> dict:
    """生成小说大纲"""
    system, prompt = build_outline_prompt(market)
    text = call_minimax(prompt, system=system, max_tokens=1500)
    if not text:
        print("[大纲] 生成失败，使用默认大纲")
        return get_default_outline()
    outline = parse_outline(text)
    if not outline:
        return get_default_outline()
    return outline


def get_default_outline() -> dict:
    """默认大纲（市场最热题材组合）"""
    return {
        "title": "都市最强系统",
        "genre": "都市异能·系统流",
        "setting": "现代都市，灵气复苏时代",
        "protagonist": "陆子昂，普通程序员，意外获得「人生重开系统」，每晚凌晨可重开一次人生",
        "core_conflict": "利用系统重开优势，在都市中步步崛起，但每次重开都会失去一段记忆",
        "main_plot": "主角利用系统重开积累优势，创建商业帝国，同时揭开系统背后的惊天秘密",
        "selling_points": ["系统流+都市", "快节奏", "不断反转", "悬念密集", "主角智商在线"],
        "target_readers": "18-35岁男性，喜欢快节奏爽文",
    }


def generate_novel(outline: dict, market: dict, chapter_num: int, previous_summary: str) -> dict:
    """生成单章小说"""
    print(f"[生成] 开始生成第{chapter_num}章...")

    writing_tips = [
        "每800字设置一个小高潮，每2000字一个大悬念",
        "主角每章至少做一件有性格的事",
        "对话要推动剧情，不写废话对话",
        "描写简洁有力，避免过度环境描写",
    ]

    system, prompt = build_chapter_prompt(
        chapter_num=chapter_num,
        total_chapters=max(10, chapter_num + 5),
        genre=outline.get("genre", "都市言情"),
        themes=market.get("top_5", []),
        story_outline=outline,
        previous_summary=previous_summary,
        writing_tips=writing_tips,
    )

    # 生成长文本（多段拼接）
    content = generate_long_text(prompt, system=system, min_chars=MIN_CHARS_PER_CHAPTER)

    if not content or len(content.strip()) < 100:
        print(f"[生成] LLM 返回内容过短，使用占位内容")
        content = _generate_placeholder_chapter(chapter_num, outline)

    char_count = count_chinese_chars(content)
    print(f"[生成] 第{chapter_num}章完成，约 {char_count} 中文字符")

    # 字数不足时续写
    if char_count < MIN_CHARS_PER_CHAPTER:
        shortfall = MIN_CHARS_PER_CHAPTER - char_count
        extension_prompt = f"""前文内容字数不足，还需再写约{shortfall}字来扩充内容。
续写要求：
- 延续当前剧情，自然过渡
- 不重复已有内容
- 保持节奏紧凑

前文末尾：
{content[-800:]}

请续写："""
        extension = call_minimax(extension_prompt, system=system, max_tokens=MAX_TOKENS_PER_CALL)
        if extension and len(extension) > 50:
            content += "\n\n" + extension
            char_count = count_chinese_chars(content)
            print(f"[生成] 续写后字数: {char_count}")

    return {
        "chapter_num": chapter_num,
        "content": content,
        "char_count": char_count,
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M"),
    }


def _generate_placeholder_chapter(chapter_num: int, outline: dict) -> str:
    """占位章节（API 不可用时）"""
    return f"""
第{chapter_num}章

【系统提示】
LLM API 当前不可用，此为占位内容。
书名：{outline.get('title', '未命名')}
类型：{outline.get('genre', '都市')}
设定：{outline.get('setting', '')}

请配置有效的 LLM API 密钥以生成真实小说内容。
"""


def save_chapter(chapter_data: dict, story_id: str, chapter_num: int, base_dir: Path) -> Path:
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
        lines = content.split("\n")
        sep_idx = next((i for i, l in enumerate(lines) if "=" in l), 0)
        body = "\n".join(lines[sep_idx + 1:])

        ch_num = int(cf.stem.split("_")[1].lstrip("0") or "1")
        full_content.append(f"\n\n{'='*50}\n第{ch_num}章\n{'='*50}\n\n")
        full_content.append(body)

        char_count = count_chinese_chars(body)
        meta["chapters"].append({"file": cf.name, "chars": char_count})
        meta["total_chars"] += char_count

    full_file = story_dir / "full_novel.txt"
    with open(full_file, "w", encoding="utf-8") as f:
        f.write("\n".join(full_content))

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

    outline_file = story_dir / "outline.json"
    with open(outline_file, "w", encoding="utf-8") as f:
        json.dump(outline, f, ensure_ascii=False, indent=2)

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

    prev_summary = ""
    if chapter_num > 1:
        prev_file = story_dir / f"chapter_{chapter_num-1:03d}.txt"
        if prev_file.exists():
            with open(prev_file, encoding="utf-8") as f:
                prev_text = f.read()
            prev_summary = prev_text[-600:] if len(prev_text) > 600 else prev_text

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

    outline = {}
    outline_path = story_dir / "outline.json"
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
