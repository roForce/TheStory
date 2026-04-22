#!/usr/bin/env python3
"""
Skill 自动更新器
每天从 GitHub Trending 抓取小说/写作相关的热门项目并安装到 skills/ 目录
"""

import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"
SKILLS_DIR.mkdir(exist_ok=True)
LOG_FILE = Path(__file__).parent.parent / "logs" / "skill_update.log"


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_github_token() -> str:
    """获取 GitHub Token"""
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return token
    # 从 gh 获取
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return ""


def search_trending_writing_repos(token: str = "") -> list[dict]:
    """搜索 GitHub 上小说/写作相关的 trending 仓库"""
    repos = []
    queries = [
        "novel OR fiction OR story writing",
        "AI story generator OR narrative",
        "writing assistant OR book writer",
    ]

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    import urllib.request

    for query in queries:
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=5"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("items", []):
                    if item.get("description") and "novel" in item["description"].lower() or \
                       "story" in item["description"].lower() or \
                       "fiction" in item["description"].lower() or \
                       "writing" in item["description"].lower():
                        repos.append({
                            "name": item["full_name"],
                            "url": item["html_url"],
                            "clone_url": item["clone_url"],
                            "stars": item.get("stargazers_count", 0),
                            "description": item.get("description", ""),
                            "pushed_at": item.get("pushed_at", ""),
                        })
                time.sleep(0.5)
        except Exception as e:
            log(f"[搜索] 查询失败: {e}")

    # 去重
    seen = set()
    unique = []
    for r in repos:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)

    # 按 stars 排序
    unique.sort(key=lambda x: x["stars"], reverse=True)
    return unique[:10]


def clone_or_update_repo(repo: dict) -> bool:
    """克隆或更新仓库"""
    name = repo["name"].split("/")[1]
    dest = SKILLS_DIR / name

    log(f"[Skill] {'更新' if dest.exists() else '安装'}: {repo['name']} ⭐{repo['stars']}")

    try:
        if dest.exists():
            # 更新
            log(f"[Skill] 仓库已存在，跳过: {name}")
            return True
        else:
            # 克隆
            log(f"[Skill] 克隆: {repo['clone_url']}")
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo["clone_url"], str(dest)],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                log(f"[Skill] ✅ 克隆成功: {name}")
                return True
            else:
                log(f"[Skill] ❌ 克隆失败: {result.stderr[:200]}")
                return False
    except Exception as e:
        log(f"[Skill] ❌ 操作失败: {e}")
        return False


def load_installed_skills() -> set:
    """加载已安装的 skills"""
    if not SKILLS_DIR.exists():
        return set()
    return {d.name for d in SKILLS_DIR.iterdir() if d.is_dir()}


def save_installed_skills(skills: list):
    """保存已安装 skills 列表"""
    record = {
        "timestamp": datetime.now().isoformat(),
        "skills": skills,
    }
    record_file = SKILLS_DIR / "installed_skills.json"
    with open(record_file, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def update_all() -> list:
    """执行完整的 skill 更新流程"""
    log("=" * 50)
    log("开始 Skill 更新")
    log("=" * 50)

    token = get_github_token()
    installed_before = load_installed_skills()
    log(f"[更新] 已安装: {len(installed_before)} 个")

    # 搜索热门仓库
    repos = search_trending_writing_repos(token)
    log(f"[搜索] 找到 {len(repos)} 个相关仓库")

    newly_installed = []
    for repo in repos:
        success = clone_or_update_repo(repo)
        if success and repo["name"] not in installed_before:
            newly_installed.append(repo["name"])

    installed_now = load_installed_skills()
    log(f"[更新] 当前共安装: {len(installed_now)} 个")

    # 记录
    save_installed_skills(list(installed_now))

    log(f"[更新] 新安装: {len(newly_installed)} 个")
    if newly_installed:
        log(f"[新增] {', '.join(newly_installed)}")

    log("Skill 更新完成")
    return newly_installed


if __name__ == "__main__":
    update_all()
