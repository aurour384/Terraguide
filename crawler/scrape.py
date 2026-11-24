"""TerraGuide 爬虫 —— 抓取 + 落盘

流程：
1. request_api()  统一封装 User-Agent / 超时 / 限速 / 重试 / 错误记录
2. list_category_members()  按分类取页面标题（支持 continue 翻页）
3. fetch_page_html()        取单页 HTML 正文
4. 落盘到 crawler/raw/{分类}/{标题}.html，并追加 crawler/raw/_manifest.jsonl 记录
   已存在的文件直接跳过，支持断点续爬

分类与排除词依据 crawler/categories.yaml，API 参数依据 plan/week01_api_notes.md。
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

API_URL = "https://terraria.wiki.gg/api.php"
WIKI_PAGE_URL = "https://terraria.wiki.gg/wiki/"

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
MANIFEST_PATH = RAW_DIR / "_manifest.jsonl"

# 来自 crawler/categories.yaml
CATEGORIES = {
    "bosses": "Category:Boss NPCs",
    "weapons": "Category:Weapon items",
    "armor": "Category:Armor sets",
}
EXCLUDE_TERMS = ("Mods", "Calamity", "Thorium", "tModLoader", "Modded")

# 每个分类本次最多抓多少页（试抓用，验证流程后可调大）
MAX_PAGES_PER_CATEGORY = 40

PROJECT_URL = "https://github.com/your-username/TerraGuide"
HEADERS = {
    # MediaWiki 要求带能识别用途和联系渠道的 User-Agent
    "User-Agent": f"TerraGuide/0.1 (Terraria wiki RAG project; {PROJECT_URL})"
}

TIMEOUT = 15          # 单个请求超时（秒）
MIN_INTERVAL = 1.0    # 连续两次请求的最小间隔（秒），重试同样遵守
MAX_RETRIES = 3       # 临时故障最多重试次数

RETRYABLE_STATUS = {500, 502, 503, 504}
RETRYABLE_API_CODES = {"ratelimited", "maxlag", "readonly"}

log = logging.getLogger("terraguide.crawler")

_last_request_at = 0.0


class ApiError(Exception):
    """请求最终失败：已重试耗尽，或属于不该重试的错误（如参数错误）。"""


def _throttle() -> None:
    """保证连续两次请求（含重试）至少间隔 MIN_INTERVAL 秒。"""
    global _last_request_at
    wait = MIN_INTERVAL - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def _retry_after_seconds(resp: requests.Response) -> float:
    """读取 429 的 Retry-After；缺失或无法解析时退回一个保守值。"""
    value = resp.headers.get("Retry-After")
    if value is not None:
        try:
            return max(float(value), MIN_INTERVAL)
        except ValueError:
            pass
    return MIN_INTERVAL * 2


def request_api(params: dict, context: str = "") -> dict:
    """请求 MediaWiki API 并返回 JSON。

    context 用于错误日志，标明请求的是哪个分类或页面。
    临时故障（超时、连接错误、5xx、429、部分 API 错误）最多重试 MAX_RETRIES 次；
    参数类错误直接抛 ApiError，不重试。
    """
    last_reason = ""

    for attempt in range(1, MAX_RETRIES + 1):
        _throttle()

        try:
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_reason = f"{type(exc).__name__}: {exc}"
            log.warning("[%s] 第 %d/%d 次请求失败：%s", context, attempt, MAX_RETRIES, last_reason)
            continue

        # 429 限流：有 Retry-After 就按它等待
        if resp.status_code == 429:
            delay = _retry_after_seconds(resp)
            last_reason = f"HTTP 429 限流（等待 {delay:.0f} 秒）"
            log.warning("[%s] 第 %d/%d 次请求失败：%s", context, attempt, MAX_RETRIES, last_reason)
            time.sleep(delay)
            continue

        if resp.status_code in RETRYABLE_STATUS:
            last_reason = f"HTTP {resp.status_code}"
            log.warning("[%s] 第 %d/%d 次请求失败：%s", context, attempt, MAX_RETRIES, last_reason)
            continue

        # 其余 4xx：参数或页面错误，重试没有意义
        if resp.status_code >= 400:
            raise ApiError(
                f"[{context}] HTTP {resp.status_code}（参数或页面错误，不重试）：{resp.text[:200]}"
            )

        try:
            data = resp.json()
        except ValueError:
            last_reason = "响应不是合法 JSON"
            log.warning("[%s] 第 %d/%d 次请求失败：%s", context, attempt, MAX_RETRIES, last_reason)
            continue

        # HTTP 200 也可能带 API 级错误
        if "error" in data:
            code = data["error"].get("code", "")
            info = data["error"].get("info", "")
            message = f"API error {code}: {info}"
            if code in RETRYABLE_API_CODES:
                last_reason = message
                log.warning("[%s] 第 %d/%d 次请求失败：%s", context, attempt, MAX_RETRIES, message)
                continue
            raise ApiError(f"[{context}] {message}")

        return data

    raise ApiError(f"[{context}] 连续 {MAX_RETRIES} 次请求均失败，最后原因：{last_reason}")


def list_category_members(category: str, limit: int) -> list[str]:
    """列出分类成员标题，按 continue 翻页，最多取 limit 条。"""
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmnamespace": 0,       # 只取主命名空间（0）的条目
        "cmlimit": min(limit, 500),
        "format": "json",
        "formatversion": 2,
    }

    titles: list[str] = []
    while len(titles) < limit:
        data = request_api(params, context=f"categorymembers:{category}")
        for item in data.get("query", {}).get("categorymembers", []):
            titles.append(item["title"])
            if len(titles) >= limit:
                break

        cont = data.get("continue")
        if not cont:
            break
        params.update(cont)     # 带上 continue / cmcontinue 继续翻页

    return titles


def fetch_page_html(title: str) -> dict:
    """取单页 HTML 正文，返回 {title, pageid, html, url}。"""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "redirects": 1,
        "format": "json",
        "formatversion": 2,
    }

    data = request_api(params, context=f"parse:{title}")
    page = data.get("parse")
    if not page:
        raise ApiError(f"[parse:{title}] 响应缺少 parse 字段")

    actual_title = page.get("title", title)
    return {
        "title": actual_title,
        "pageid": page.get("pageid"),
        "html": page.get("text", ""),
        "url": WIKI_PAGE_URL + quote(actual_title.replace(" ", "_")),
    }


def _is_excluded(title: str) -> bool:
    """标题命中排除词则跳过（对应 categories.yaml 的 exclude_title_terms）。"""
    lowered = title.lower()
    return any(term.lower() in lowered for term in EXCLUDE_TERMS)


def _safe_filename(title: str) -> str:
    """把页面标题转成 Windows 下合法的文件名。"""
    invalid = '<>:"/\\|?*'
    name = "".join("_" if ch in invalid else ch for ch in title).strip(" .")
    return name[:100] or "_untitled"


def append_manifest(record: dict) -> None:
    """追加一条抓取记录到 _manifest.jsonl，便于追溯和统计。"""
    record = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record}
    with MANIFEST_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main(limit: int) -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    stats = {"success": 0, "skip_exists": 0, "skip_excluded": 0, "failed": 0}

    for slug, category in CATEGORIES.items():
        print(f"\n=== {category} ===")
        try:
            titles = list_category_members(category, limit)
        except ApiError as exc:
            log.error("列出分类成员失败：%s", exc)
            stats["failed"] += 1
            continue

        print(f"本批 {len(titles)} 个页面")
        out_dir = RAW_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        for title in titles:
            if _is_excluded(title):
                log.info("跳过（命中排除词）：%s", title)
                append_manifest({"title": title, "category": category, "status": "skip_excluded"})
                stats["skip_excluded"] += 1
                continue

            path = out_dir / f"{_safe_filename(title)}.html"
            rel_path = path.relative_to(BASE_DIR).as_posix()  # 统一用 /，便于跨平台和 Git 记录
            if path.exists():
                print(f"  - 已存在，跳过：{title}")
                append_manifest({
                    "title": title,
                    "category": category,
                    "file": rel_path,
                    "status": "skip_exists",
                })
                stats["skip_exists"] += 1
                continue

            try:
                page = fetch_page_html(title)
            except ApiError as exc:
                log.error("抓取失败：%s → %s", title, exc)
                append_manifest({
                    "title": title,
                    "category": category,
                    "status": "failed",
                    "reason": str(exc),
                })
                stats["failed"] += 1
                continue

            path.write_text(page["html"], encoding="utf-8")
            append_manifest({
                "title": page["title"],
                "pageid": page["pageid"],
                "category": category,
                "url": page["url"],
                "file": rel_path,
                "status": "success",
            })
            stats["success"] += 1
            print(f"  ✓ {title}")

    print("\n=== 汇总 ===")
    print(f"成功 {stats['success']} · 已存在跳过 {stats['skip_exists']} · "
          f"排除词跳过 {stats['skip_excluded']} · 失败 {stats['failed']}")
    print(f"原始数据目录：{RAW_DIR}")
    print(f"抓取记录：{MANIFEST_PATH}")

    return 0 if stats["failed"] == 0 else 1


def pause_before_exit() -> None:
    """双击运行时窗口默认会立刻关闭，停一下方便查看输出。"""
    try:
        input("\n按回车键退出...")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)

    parser = argparse.ArgumentParser(description="TerraGuide Wiki 爬虫（抓取 + 落盘）")
    parser.add_argument(
        "--limit", type=int, default=MAX_PAGES_PER_CATEGORY,
        help=f"每个分类最多抓取的页面数（默认 {MAX_PAGES_PER_CATEGORY}）",
    )
    args = parser.parse_args()

    try:
        sys.exit(main(args.limit))
    finally:
        pause_before_exit()
