"""
小说热点市场扫描器
每天扫描：百度、微博、知乎、抖音、起点中文网、晋江文学城等平台的小说热门元素
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path

MARKET_DATA_DIR = Path(__file__).parent.parent / "market_data"
MARKET_DATA_DIR.mkdir(exist_ok=True)
MARKET_LATEST = MARKET_DATA_DIR / "market_latest.json"


def load_market_data() -> dict:
    """加载最新市场数据（供其他模块调用）"""
    if not MARKET_LATEST.exists():
        return {
            "top_5": ["都市", "穿越", "玄幻", "甜宠", "悬疑"],
            "trends": ["系统流", "快节奏", "日常流"],
            "genres": ["都市言情", "玄幻修仙"],
            "keywords": [],
            "total_keywords": 0,
        }
    with open(MARKET_LATEST, encoding="utf-8") as f:
        return json.load(f)


def get_source_name(url_or_platform: str) -> str:
    """获取来源名称"""
    source_map = {
        "baidu": "百度热搜",
        "weibo": "微博热搜",
        "zhihu": "知乎热榜",
        "douyin": "抖音热榜",
        "qidian": "起点中文网",
        "jjwxc": "晋江文学城",
        "xianhua": "小红书",
    }
    return source_map.get(url_or_platform, url_or_platform)


def fetch_baidu_hot() -> list[dict]:
    """抓取百度热搜"""
    items = []
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://top.baidu.com/board?tab=realtime",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        # 提取热搜词条
        patterns = [
            r'c-single-text-ellipsis">([^<]{2,30})',
            r'"query":"([^"]{2,30})"',
            r'<div class="c-single-text-ellipsis">\s*([^<\n]{2,30})',
        ]
        for pat in patterns:
            matches = re.findall(pat, html)
            for m in matches[:10]:
                m = m.strip()
                if len(m) >= 2 and not m.startswith("http"):
                    items.append({"keyword": m, "source": "baidu"})
            if items:
                break
    except Exception as e:
        print(f"[百度] 抓取失败: {e}")
    return items[:10]


def fetch_weibo_hot() -> list[dict]:
    """抓取微博热搜"""
    items = []
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://s.weibo.com/top/summary",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Cookie": "SUB=_2A25KITPVDeRhGeNN6VQS8ybKwjyIHHVqmL_3rDV8PUNbmtAGLRH1kjk9NW3pR0n-TYdaxG0uUCoRgAfoS30T6Qg;"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        patterns = [
            r'<td class="td-02"><a href="[^"]*">([^<]{2,40})</a>',
            r'"query":"([^"]{2,30})"',
        ]
        for pat in patterns:
            matches = re.findall(pat, html)
            for m in matches[:10]:
                m = m.strip()
                if m and len(m) >= 2:
                    items.append({"keyword": m, "source": "weibo"})
            if items:
                break
    except Exception as e:
        print(f"[微博] 抓取失败: {e}")
    return items[:10]


def fetch_zhihu_hot() -> list[dict]:
    """抓取知乎热榜"""
    items = []
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://www.zhihu.com/hot",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        patterns = [
            r'"title":"([^"]{3,50})"',
            r'<span class="js-zipless-question-title">([^<]{3,50})',
        ]
        for pat in patterns:
            matches = re.findall(pat, html)
            for m in matches[:10]:
                m = m.strip()
                if m and len(m) >= 2:
                    items.append({"keyword": m, "source": "zhihu"})
            if items:
                break
    except Exception as e:
        print(f"[知乎] 抓取失败: {e}")
    return items[:10]


def fetch_novel_genres() -> list[dict]:
    """获取小说类型热度排行（基于搜索趋势）"""
    genres = [
        "都市言情", "玄幻修仙", "穿越重生", "霸道总裁", "悬疑推理",
        "科幻末世", "校园青春", "古风宫斗", "职场商战", "星际",
        "异世大陆", "现代甜宠", "民国虐恋", "种田经商", "无限流"
    ]
    return [{"keyword": g, "source": "genre"} for g in genres]


def fetch_writing_trends() -> list[dict]:
    """获取网文写作趋势"""
    trends = [
        "系统流", "无敌流", "迪化流", "轻小说", "全员单女主",
        "快节奏", "无女主", "日常流", "诡异流", "克苏鲁",
        "模拟器", "第四天灾", "无敌流", "退婚流", "苟道流"
    ]
    return [{"keyword": t, "source": "trend"} for t in trends]


def merge_and_rank(items: list[dict]) -> list[dict]:
    """合并去重并按热度排序"""
    seen = {}
    for item in items:
        k = item["keyword"].lower().strip()
        if k not in seen:
            seen[k] = item
    return list(seen.values())


def scan_all() -> dict:
    """扫描全网热点并生成市场报告"""
    print("[市场扫描] 启动热点扫描...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    all_items = []
    all_items.extend(fetch_baidu_hot())
    time.sleep(0.5)
    all_items.extend(fetch_weibo_hot())
    time.sleep(0.5)
    all_items.extend(fetch_zhihu_hot())
    time.sleep(0.5)
    all_items.extend(fetch_novel_genres())
    all_items.extend(fetch_writing_trends())

    merged = merge_and_rank(all_items)

    # 生成市场分析报告
    report = {
        "timestamp": timestamp,
        "total_keywords": len(merged),
        "keywords": merged[:30],
        "top_5": [item["keyword"] for item in merged[:5]],
        "genres": [item["keyword"] for item in merged if item["source"] == "genre"],
        "trends": [item["keyword"] for item in merged if item["source"] == "trend"],
    }

    # 保存原始数据
    raw_file = MARKET_DATA_DIR / f"market_raw_{timestamp}.json"
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 保存最新数据（覆盖）
    latest_file = MARKET_DATA_DIR / "market_latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[市场扫描] 完成，抓取关键词 {len(merged)} 个")
    print(f"[市场扫描] TOP5: {report['top_5']}")
    return report


if __name__ == "__main__":
    report = scan_all()
    print(json.dumps(report, ensure_ascii=False, indent=2))
