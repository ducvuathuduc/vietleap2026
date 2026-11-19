"""Social enrichment (mentor method E): VnExpress/CafeF RSS -> weekly sector keyword counts."""
from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import httpx
from unidecode import unidecode

from .output import KIT, save_raw

TZ = ZoneInfo("Asia/Saigon")
OUT = KIT / "data" / "raw" / "news" / "news_weekly.csv"
FEEDS = [
    ("vnexpress_kinh_doanh", "https://vnexpress.net/rss/kinh-doanh.rss"),
    ("cafef_thi_truong", "https://cafef.vn/thi-truong-chung-khoan.rss"),
]
UA = "vietleap-research/0.1 (press monitor; +https://github.com/vietleap)"
WEEKS_BACK = 12

SECTORS = {
    "banking": ["ngan hang", "tin dung", "nim", "npl", "casa", "lai suat huy dong", "sbv"],
    "real_estate": ["bat dong san", "can ho", "chung cu", "nha o", "dat dai", "savills", "cbre", "gia nha"],
    "capital_market": ["chung khoan", "vn-index", "vnindex", "khoi ngoai", "margin", "co phieu",
                       "trai phieu", "niem yet", "thanh khoan"],
    "fdi": ["fdi", "dau tu nuoc ngoai", "von dang ky", "nha dau tu"],
    "public_investment": ["dau tu cong", "giai ngan", "ngan sach", "nsnn", "dau thau"],
    "macro": ["cpi", "lam phat", "gdp", "tang truong kinh te", "xuat khau", "nhap khau", "iip"],
}
STOPWORDS = {"va", "cua", "la", "cac", "cho", "voi", "trong", "khi", "tren", "duoc", "tai", "co", "nhung",
             "mot", "nhu", "de", "tu", "den", "theo", "ve", "se", "da", "dang", "bi", "boi", "hon", "sau",
             "truoc", "giua", "nay", "do", "ra", "vao", "len", "xuong", "tang", "giam", "moi", "cung",
             "nam", "nhat", "vua", "nguoi", "luc", "sap", "hom", "ngay", "thang", "quy", "trieu", "ty"}


def plain(text: str) -> str:
    return unidecode(unescape(re.sub(r"<[^>]+>", " ", text or ""))).lower()


def sector_for(title: str) -> str:
    text = plain(title)
    scores = {name: sum(1 for keyword in words if keyword in text) for name, words in SECTORS.items()}
    best = max(scores, key=lambda name: scores[name])
    return best if scores[best] else "other"


def _keywords(entries) -> str:
    words = Counter()
    for entry in entries:
        for token in re.findall(r"[a-z0-9]{3,}", plain(f"{entry['title']} {entry['summary']}")):
            if token not in STOPWORDS and not token.isdigit():
                words[token] += 1
    return "; ".join(word for word, _ in sorted(words.items(), key=lambda kv: (-kv[1], kv[0]))[:5])


def parse_feed(content: bytes, source: str) -> list[dict]:
    parsed = feedparser.parse(content)
    entries = []
    for item in parsed.entries:
        stamp = item.get("published_parsed") or item.get("updated_parsed")
        if not stamp:
            continue
        published = datetime(*stamp[:6], tzinfo=ZoneInfo("UTC")).astimezone(TZ)
        entries.append({
            "source": source,
            "title": unescape(item.get("title") or ""),
            "summary": unescape(item.get("summary") or ""),
            "link": item.get("link") or "",
            "published": published,
            "week": f"{published.isocalendar().year}-W{published.isocalendar().week:02d}",
            "sector": sector_for(item.get("title") or ""),
        })
    return entries


def weekly_rows(entries) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for entry in entries:
        groups.setdefault((entry["week"], entry["sector"]), []).append(entry)
    rows = [{"week": week, "sector": sector, "article_count": len(group),
             "top_5_keywords": _keywords(group)}
            for (week, sector), group in groups.items()]
    return sorted(rows, key=lambda r: (r["week"], r["sector"]))


def fetch_feed(url: str) -> tuple[bytes | None, str]:
    try:
        response = httpx.get(url, headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
        if response.status_code == 200:
            return response.content, "200"
        return None, f"http {response.status_code}"
    except httpx.HTTPError as exc:
        return None, f"error {type(exc).__name__}"


def run(out_path: Path = OUT, weeks_back: int = WEEKS_BACK) -> tuple[int, list[dict]]:
    """Fetch all feeds, keep the last ``weeks_back`` ISO weeks, write the weekly CSV."""
    cutoff = datetime.now(TZ) - timedelta(weeks=weeks_back)
    entries, status = [], []
    for source, url in FEEDS:
        content, state = fetch_feed(url)
        status.append({"source": source, "url": url, "status": state, "articles": 0})
        if content:
            save_raw(f"{source}_rss", content, "xml")
            parsed = parse_feed(content, source)
            status[-1]["articles"] = len(parsed)
            entries += [entry for entry in parsed if entry["published"] >= cutoff]
    rows = weekly_rows(entries)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["week", "sector", "article_count", "top_5_keywords"],
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows), status
