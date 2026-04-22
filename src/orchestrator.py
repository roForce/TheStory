#!/usr/bin/env python3
"""
TheStory 主调度器
- 每天扫描市场热点
- 每10分钟生成/更新一章
- 每次覆盖所有章节并推送 GitHub
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
    create_new_story, update_story_chapter, build_full_novel,
    get_story_progress, generate_outline, CHAPTERS_DIR, count_chinese_chars
)

WORKSPACE = Path(__file__).parent.parent
GITHUB_REMOTE = "https://github.com/roForce/TheStory.git"
LOG_FILE = WORKSPACE / "logs" / "orchestrator.log"


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_story_id() -> str:
    """获取当前活跃故事ID（基于最新章节时间）"""
    chapters = WORKSPACE / "chapters"
    if not chapters.exists():
        return datetime.now().strftime("story_%Y%m%d%H%M")

    story_dirs = sorted([d for d in chapters.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime)
    if not story_dirs:
        return datetime.now().strftime("story_%Y%m%d%H%M")

    return story_dirs[-1].name


def ensure_github_repo():
    """确保 GitHub 仓库存在且本地已初始化"""
    git_dir = WORKSPACE / ".git"
    if not git_dir.exists():
        import subprocess
        subprocess.run(["git", "init"], cwd=WORKSPACE, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "roForce"], cwd=WORKSPACE, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "roForce@users.noreply.github.com"], cwd=WORKSPACE, check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", GITHUB_REMOTE], cwd=WORKSPACE, check=True, capture_output=True)
        log("[Git] 本地仓库已初始化")


def push_to_github(story_id: str) -> bool:
    """推送故事到 GitHub"""
    import subprocess

    try:
        # 阶段1: 所有更改（包括所有章节）
        subprocess.run(["git", "add", "-A"], cwd=WORKSPACE, check=True, capture_output=True)

        # 检查是否有更改
        status = subprocess.run(
            ["git", "diff", "--cached", "--stat"],
            cwd=WORKSPACE, capture_output=True, text=True
        )
        if not status.stdout.strip():
            log("[Git] 没有新内容需要提交")
            return True

        # 提交
        subprocess.run(
            ["git", "commit", "-m", f"feat: {story_id} auto-update {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
            cwd=WORKSPACE, check=True, capture_output=True
        )
        log(f"[Git] 已提交: {story_id}")

        # 推送（使用 SSH 或 HTTPS）
        for remote_url in [
            GITHUB_REMOTE,
            f"git@github.com:roForce/TheStory.git",
        ]:
            result = subprocess.run(
                ["git", "push", "-u", remote_url, "main", "--force"],
                cwd=WORKSPACE, capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                log(f"[Git] 推送成功 → {remote_url}")
                return True
            log(f"[Git] 推送失败: {result.stderr[:200]}")

        return False
    except subprocess.TimeoutExpired:
        log("[Git] 推送超时")
        return False
    except Exception as e:
        log(f"[Git] 推送异常: {e}")
        return False


def run_init():
    """初始化新小说"""
    log("=" * 50)
    log("开始新的小说创作周期")
    log("=" * 50)

    # 市场扫描
    log("[市场扫描] 启动热点扫描...")
    market_data = scan_all()
    log(f"[市场] TOP5 热点: {market_data.get('top_5', [])[:5]}")

    # 生成大纲
    log("[大纲] 正在生成小说大纲...")
    outline = generate_outline(market_data)
    log(f"[大纲] 生成的标题: {outline.get('title', 'N/A')}")

    # 创建新故事
    story_id = datetime.now().strftime("story_%Y%m%d%H%M")
    result = create_new_story(outline, market_data, story_id)
    log(f"[故事] 创建完成: {result['status']}")

    # 合并并推送
    build_full_novel(story_id, CHAPTERS_DIR)
    ensure_github_repo()
    push_to_github(story_id)

    log(f"[完成] 故事 {story_id} 第1章已生成并推送")
    return result


def run_update():
    """更新当前章节"""
    story_id = get_story_id()
    progress = get_story_progress(story_id)

    if not progress["exists"]:
        log(f"[更新] 故事不存在，执行初始化")
        return run_init()

    current = progress.get("meta", {}).get("chapters", [])
    current_chapter = len(current) + 1

    market_data = load_market_data()
    outline = progress.get("outline", {})

    if not outline:
        log("[更新] 无大纲，执行初始化")
        return run_init()

    log(f"[更新] 继续故事 {story_id}，生成第 {current_chapter} 章...")

    update_story_chapter(story_id, outline, market_data, current_chapter)

    # 合并推送
    build_full_novel(story_id, CHAPTERS_DIR)
    push_to_github(story_id)

    log(f"[完成] 故事 {story_id} 第 {current_chapter} 章已更新并推送")
    return {"story_id": story_id, "chapter": current_chapter}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["init", "update"])
    args = parser.parse_args()

    if args.action == "init":
        run_init()
    else:
        run_update()
