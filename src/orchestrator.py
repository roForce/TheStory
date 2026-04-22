#!/usr/bin/env python3
"""
TheStory 主调度器
- 每天扫描市场热点
- 每10分钟生成/更新一章
- 每次覆盖所有章节并推送
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from market_scanner import scan_all, load_market_data
from novel_engine import (
    create_new_story,
    update_story_chapter,
    get_story_progress,
    build_full_novel,
    build_outline_prompt,
    call_llm,
    CHAPTERS_DIR,
)

WORKSPACE = Path(__file__).parent.parent
GITHUB_DIR = WORKSPACE
GITHUB_USER = "roForce"
GITHUB_REPO = "TheStory"
LOG_FILE = WORKSPACE / "logs" / "story.log"

LOG_FILE.parent.mkdir(exist_ok=True)


def log(msg: str):
    """写日志"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def parse_outline_from_json(json_str: str) -> dict:
    """从 LLM 返回的 JSON 中提取大纲"""
    try:
        # 尝试直接解析
        return json.loads(json_str)
    except:
        pass

    # 尝试从文本中提取 JSON 块
    import re
    patterns = [
        r'\{[^{}]*"title"[^{}]*\}',
        r'```json\s*([\s\S]*?)\s*```',
        r'(\{[\s\S]*\})',
    ]
    for pat in patterns:
        matches = re.findall(pat, json_str)
        for m in matches:
            try:
                result = json.loads(m)
                if "title" in result:
                    return result
            except:
                continue
    return {}


def generate_outline(market: dict) -> dict:
    """使用 LLM 生成小说大纲"""
    log("[大纲] 正在生成小说大纲...")
    prompt = build_outline_prompt(market)

    system_prompt = """你是一个专业的网文策划师，熟悉起点中文网、晋江文学城等平台的爆款作品规律。
输出必须是合法的、可以直接解析的 JSON 格式，不要包含任何解释性文字。"""

    raw = call_llm(prompt, system=system_prompt)
    if not raw:
        log("[大纲] LLM 调用失败，使用默认大纲")
        return get_default_outline(market)

    outline = parse_outline_from_json(raw)
    if not outline or "title" not in outline:
        log("[大纲] 解析大纲失败，使用默认大纲")
        return get_default_outline(market)

    log(f"[大纲] 生成成功：《{outline.get('title', '未知')}》")
    return outline


def get_default_outline(market: dict) -> dict:
    """生成默认大纲（基于市场热点）"""
    top = market.get("top_5", ["都市", "穿越"])[0] if market.get("top_5") else "都市"
    genre = market.get("genres", ["都市言情"])[0] if market.get("genres") else "都市言情"
    trend = market.get("trends", ["系统流"])[0] if market.get("trends") else "系统流"

    return {
        "title": f"《{top}王者》",
        "genre": genre,
        "setting": f"现代{top}都市，主角意外获得{trend}，开启传奇人生",
        "protagonist": "林逸，普通大学生，意外激活{trend}系统，从此改变命运",
        "core_conflict": "主角利用系统逆袭，但背后有神秘势力在操控一切",
        "main_plot": "从平凡大学生到站在世界之巅的热血逆袭之路",
        "chapters_plan": [
            "第1章：命运转折，激活系统",
            "第2章：初露锋芒，震惊众人",
            "第3章：第一桶金，暗流涌动",
            "第4章：强敌出现，绝地反击",
            "第5章：势力觉醒，风云际会",
        ],
        "selling_points": [trend, "逆袭", "热血", "爽文", "快节奏"],
        "target_readers": "18-35岁男性读者，喜欢热血逆袭类网文",
        "word_count_target": "100万字+",
    }


def get_or_create_story_id() -> str:
    """获取或创建故事 ID"""
    progress_file = WORKSPACE / "current_story.json"

    if progress_file.exists():
        with open(progress_file, encoding="utf-8") as f:
            data = json.load(f)
            story_id = data.get("story_id", "")
            if story_id:
                log(f"[故事] 继续当前故事: {story_id}")
                return story_id

    # 新故事
    story_id = f"story_{datetime.now().strftime('%Y%m%d%H%M')}"
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump({"story_id": story_id, "created": datetime.now().isoformat()}, f)
    log(f"[故事] 创建新故事: {story_id}")
    return story_id


def update_story(outline: dict, market: dict, story_id: str) -> dict:
    """更新小说：生成下一章或刷新已有章节"""
    progress = get_story_progress(story_id)
    current_ch = progress.get("chapters", 0)

    next_ch = current_ch + 1
    log(f"[更新] 当前第{current_ch}章，生成第{next_ch}章")

    result = update_story_chapter(story_id, outline, market, next_ch)

    # 更新进度
    progress_file = WORKSPACE / "current_story.json"
    with open(progress_file, encoding="utf-8") as f:
        data = json.load(f)
    data["current_chapter"] = next_ch
    data["last_update"] = datetime.now().isoformat()
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return result


def build_and_overwrite(story_id: str):
    """构建完整小说并覆盖更新"""
    log("[构建] 合并所有章节为完整小说...")
    full_file = build_full_novel(story_id, CHAPTERS_DIR)

    # 复制到 githubstory 根目录（覆盖）
    dest = WORKSPACE / f"{story_id}_full_novel.txt"
    with open(full_file, encoding="utf-8") as src:
        content = src.read()
    with open(dest, "w", encoding="utf-8") as f:
        f.write(content)

    log(f"[构建] 完整小说已生成: {dest.name} ({len(content)} 字符)")
    return dest


def git_push(story_id: str, chapter_num: int):
    """提交并推送所有更新"""
    import subprocess

    log("[Git] 开始推送...")

    # 确保在正确目录
    try:
        # 添加所有更改
        subprocess.run(["git", "add", "-A"], cwd=WORKSPACE, check=True)
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=WORKSPACE, capture_output=True, text=True
        )
        if not status.stdout.strip():
            log("[Git] 没有更改，跳过推送")
            return

        subprocess.run(
            ["git", "commit", "-m", f"update: {story_id} chapter {chapter_num} ({datetime.now().strftime('%Y%m%d %H:%M')})"],
            cwd=WORKSPACE, check=True
        )

        # 设置 origin（如果不存在）
        remote_check = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=WORKSPACE, capture_output=True, text=True
        )
        if "not exist" in remote_check.stderr.lower():
            subprocess.run(
                ["git", "remote", "add", "origin",
                 f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}.git"],
                cwd=WORKSPACE, check=False
            )

        result = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            log(f"[Git] ✅ 推送成功")
        else:
            log(f"[Git] ⚠️ 推送失败: {result.stderr[:200]}")
    except subprocess.CalledProcessError as e:
        log(f"[Git] ⚠️ Git 操作失败: {e}")


def ensure_git_repo():
    """确保本地是 Git 仓库并连接到 GitHub"""
    import subprocess

    git_dir = WORKSPACE / ".git"
    if not git_dir.exists():
        log("[Git] 初始化仓库...")
        subprocess.run(["git", "init"], cwd=WORKSPACE, check=True)
        subprocess.run(["git", "remote", "add", "origin",
                       f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}.git"],
                      cwd=WORKSPACE, check=False)

    # 设置用户信息
    subprocess.run(["git", "config", "user.name", "roForce"], cwd=WORKSPACE, check=False)
    subprocess.run(["git", "config", "user.email", "roForce@users.noreply.github.com"],
                   cwd=WORKSPACE, check=False)


def initialize_story():
    """初始化新故事（扫描市场 + 生成大纲 + 第1章）"""
    log("=" * 50)
    log("开始新的小说创作周期")
    log("=" * 50)

    # 1. 扫描市场
    market = scan_all()
    log(f"[市场] TOP5 热点: {market.get('top_5', [])}")

    # 2. 生成大纲
    outline = generate_outline(market)
    story_id = get_or_create_story_id()

    # 3. 创建故事
    result = create_new_story(outline, market, story_id)
    log(f"[故事] 创建完成: {result['status']}")

    return story_id, outline, market


def run_update_cycle():
    """运行一次更新周期"""
    log("-" * 50)
    log("开始更新周期")

    # 确保 Git 仓库已初始化
    ensure_git_repo()

    # 加载市场数据
    market = load_market_data()
    if not market or not market.get("top_5"):
        log("[市场] 市场数据为空，先做市场扫描")
        market = scan_all()

    # 获取或创建故事
    story_id = get_or_create_story_id()
    progress = get_story_progress(story_id)

    # 检查是否需要生成新故事（每天生成一次新故事）
    progress_file = WORKSPACE / "current_story.json"
    should_restart = False
    if progress_file.exists():
        with open(progress_file, encoding="utf-8") as f:
            data = json.load(f)
        created = data.get("created", "")
        if created:
            from datetime import datetime
            try:
                created_date = datetime.fromisoformat(created).date()
                if (datetime.now().date() - created_date).days >= 1:
                    log("[故事] 超过1天，生成新故事")
                    should_restart = True
            except:
                pass

    if should_restart or not progress.get("exists"):
        story_id, outline, market = initialize_story()
    else:
        # 加载大纲
        outline_path = CHAPTERS_DIR / story_id / "outline.json"
        outline = {}
        if outline_path.exists():
            with open(outline_path, encoding="utf-8") as f:
                outline = json.load(f)
        else:
            outline = get_default_outline(market)

    # 更新章节
    result = update_story(outline, market, story_id)

    # 构建完整小说
    build_and_overwrite(story_id)

    # 推送
    git_push(story_id, result.get("chapter_num", 0))

    log("更新周期完成")
    return True


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "update"

    if mode == "init":
        initialize_story()
    elif mode == "update":
        run_update_cycle()
    elif mode == "scan":
        scan_all()
    else:
        print(f"Usage: {sys.argv[0]} [init|update|scan]")
