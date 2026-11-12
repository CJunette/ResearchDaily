#!/usr/bin/env python3
"""State, deduplication, collection, review validation, and brief rendering.

The model/browser workflow reads full papers and writes structured review JSON.
This helper deliberately does not generate scientific summaries from abstracts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import math
import re
import sqlite3
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "papers.sqlite"
INTERESTS_PATH = ROOT / "config" / "interests.json"
SOURCES_PATH = ROOT / "config" / "sources.json"
DISCOVERY_PATH = ROOT / "config" / "discovery.json"
SITE_DIST = ROOT / "sites" / "research-daily" / "site"
BRIEF_ROLES = ("core", "adjacent", "heavyweight", "serendipity", "ai_frontier")


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    canonical_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    authors_json TEXT NOT NULL,
    publication_year INTEGER,
    publication_date TEXT,
    venue TEXT,
    work_type TEXT,
    doi TEXT,
    arxiv_id TEXT,
    source_url TEXT NOT NULL,
    pdf_url TEXT,
    source_name TEXT NOT NULL,
    track TEXT NOT NULL,
    citations INTEGER,
    citation_source TEXT,
    citation_checked_at TEXT,
    venue_score REAL NOT NULL DEFAULT 0,
    is_retracted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
    paper_id TEXT PRIMARY KEY REFERENCES papers(id) ON DELETE CASCADE,
    full_text_read INTEGER NOT NULL CHECK(full_text_read = 1),
    full_text_url TEXT NOT NULL,
    access_method TEXT NOT NULL,
    read_at TEXT NOT NULL,
    plain_language_takeaway TEXT NOT NULL,
    problem TEXT NOT NULL,
    method TEXT NOT NULL,
    contributions_json TEXT NOT NULL,
    delta TEXT NOT NULL,
    evidence TEXT NOT NULL,
    limitations TEXT NOT NULL,
    why_read TEXT NOT NULL,
    sections_to_read TEXT NOT NULL,
    reading_minutes INTEGER NOT NULL,
    quality_score REAL NOT NULL,
    relevance_score REAL NOT NULL,
    innovation_score REAL NOT NULL,
    reviewer_notes TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recommendations (
    brief_date TEXT NOT NULL,
    paper_id TEXT NOT NULL UNIQUE REFERENCES papers(id),
    section TEXT NOT NULL,
    position INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (brief_date, position)
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT REFERENCES papers(id),
    value TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS discovery_sources (
    source_key TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    cursor TEXT NOT NULL,
    complete INTEGER NOT NULL CHECK(complete IN (0, 1)),
    notes TEXT NOT NULL,
    checked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS discovery_decisions (
    paper_id TEXT NOT NULL REFERENCES papers(id),
    source_key TEXT NOT NULL REFERENCES discovery_sources(source_key),
    topic TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('shortlist', 'defer', 'reject', 'access_blocked')),
    reason TEXT NOT NULL,
    retry_after TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(paper_id, source_key)
);
"""


REQUIRED_REVIEW_FIELDS = (
    "paper_id",
    "full_text_read",
    "full_text_url",
    "access_method",
    "read_at",
    "plain_language_takeaway",
    "problem",
    "method",
    "contributions",
    "delta",
    "evidence",
    "limitations",
    "why_read",
    "sections_to_read",
    "reading_minutes",
    "quality_score",
    "relevance_score",
    "innovation_score",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return value.removeprefix("doi:").strip() or None


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def canonical_key(item: dict[str, Any]) -> str:
    doi = normalize_doi(item.get("doi"))
    if doi:
        return f"doi:{doi}"
    arxiv_id = (item.get("arxiv_id") or "").strip().lower()
    if arxiv_id:
        return f"arxiv:{arxiv_id.split('v')[0]}"
    authors = item.get("authors") or []
    first_author = authors[0] if authors else "unknown"
    identity = "|".join(
        [normalize_title(item["title"]), normalize_title(first_author), str(item.get("publication_year") or "")]
    )
    return "title:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def paper_id_from_key(key: str) -> str:
    return "p_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def venue_score(venue: str, config: dict[str, Any]) -> float:
    venue_lower = venue.lower()
    for journal in config.get("journal_catalogs", []):
        if journal["name"].lower() == venue_lower:
            return 9.0 if journal.get("rotation") == "primary" else 7.0
    for candidate in config.get("venues", {}).get("high_priority", []):
        if candidate.lower() in venue_lower:
            return 9.0
    for candidate in config.get("venues", {}).get("secondary", []):
        if candidate.lower() in venue_lower:
            return 7.0
    return 4.0


DISCOVERY_STOPWORDS = {
    "artificial", "human", "intelligence", "learning", "model", "models",
    "method", "methods", "research", "scientific", "system", "systems",
    "review", "new", "technology", "behaviour",
}


def passes_discovery_prefilter(
    item: dict[str, Any], sources: dict[str, Any], interests: dict[str, Any], today: dt.date
) -> bool:
    """Reject obvious search noise before expensive full-text screening."""
    publication_date = item.get("publication_date")
    if publication_date:
        try:
            if dt.date.fromisoformat(publication_date) > today:
                return False
        except ValueError:
            return False
    if item.get("is_retracted"):
        return False
    if venue_score(item.get("venue") or "", sources) >= 7.0:
        return True
    track = interests.get("tracks", {}).get(item.get("track"), {})
    feature_tokens = {
        token
        for phrase in track.get("keywords", [])
        for token in re.findall(r"[a-z0-9-]+", phrase.lower())
        if len(token) >= 5 and token not in DISCOVERY_STOPWORDS
    }
    haystack = " ".join([item.get("title") or "", item.get("abstract") or ""]).lower()
    return any(re.search(rf"\b{re.escape(token)}\b", haystack) for token in feature_tokens)


def validate_candidate(item: dict[str, Any]) -> None:
    for field in ("title", "authors", "source_url", "source_name", "track"):
        if not item.get(field):
            raise ValueError(f"candidate missing required field: {field}")
    if not isinstance(item["authors"], list):
        raise ValueError("candidate authors must be a list")


def upsert_candidate(conn: sqlite3.Connection, item: dict[str, Any], sources: dict[str, Any]) -> str:
    validate_candidate(item)
    key = canonical_key(item)
    paper_id = paper_id_from_key(key)
    timestamp = now_iso()
    doi = normalize_doi(item.get("doi"))
    score = float(item.get("venue_score", venue_score(item.get("venue") or "", sources)))
    conn.execute(
        """
        INSERT INTO papers (
            id, canonical_key, title, authors_json, publication_year, publication_date,
            venue, work_type, doi, arxiv_id, source_url, pdf_url, source_name,
            track, citations, citation_source, citation_checked_at, venue_score,
            is_retracted, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(canonical_key) DO UPDATE SET
            title = excluded.title,
            authors_json = excluded.authors_json,
            publication_year = COALESCE(excluded.publication_year, papers.publication_year),
            publication_date = COALESCE(excluded.publication_date, papers.publication_date),
            venue = CASE WHEN excluded.venue != '' THEN excluded.venue ELSE papers.venue END,
            work_type = COALESCE(excluded.work_type, papers.work_type),
            source_url = excluded.source_url,
            pdf_url = COALESCE(excluded.pdf_url, papers.pdf_url),
            citations = COALESCE(excluded.citations, papers.citations),
            citation_source = COALESCE(excluded.citation_source, papers.citation_source),
            citation_checked_at = COALESCE(excluded.citation_checked_at, papers.citation_checked_at),
            venue_score = MAX(excluded.venue_score, papers.venue_score),
            is_retracted = MAX(excluded.is_retracted, papers.is_retracted),
            updated_at = excluded.updated_at
        """,
        (
            paper_id,
            key,
            item["title"].strip(),
            json.dumps(item["authors"], ensure_ascii=False),
            item.get("publication_year"),
            item.get("publication_date"),
            item.get("venue") or "",
            item.get("work_type"),
            doi,
            item.get("arxiv_id"),
            item["source_url"],
            item.get("pdf_url"),
            item["source_name"],
            item["track"],
            item.get("citations"),
            item.get("citation_source"),
            item.get("citation_checked_at"),
            score,
            int(bool(item.get("is_retracted", False))),
            timestamp,
            timestamp,
        ),
    )
    row = conn.execute("SELECT id FROM papers WHERE canonical_key = ?", (key,)).fetchone()
    assert row is not None
    return str(row["id"])


def read_json_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    return payload if isinstance(payload, list) else [payload]


def inverted_abstract(index: dict[str, list[int]] | None) -> str | None:
    if not index:
        return None
    positions: list[tuple[int, str]] = []
    for word, indices in index.items():
        positions.extend((position, word) for position in indices)
    return " ".join(word for _, word in sorted(positions))


def openalex_to_candidate(work: dict[str, Any], track: str) -> dict[str, Any]:
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    best_oa = work.get("best_oa_location") or {}
    doi = normalize_doi(work.get("doi"))
    return {
        "title": work.get("display_name") or work.get("title"),
        "authors": [
            (entry.get("author") or {}).get("display_name")
            for entry in work.get("authorships", [])
            if (entry.get("author") or {}).get("display_name")
        ],
        "publication_year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "venue": source.get("display_name") or "",
        "work_type": work.get("type"),
        "doi": doi,
        "source_url": work.get("doi") or primary.get("landing_page_url") or work.get("id"),
        "pdf_url": best_oa.get("pdf_url") or primary.get("pdf_url"),
        "source_name": "OpenAlex",
        "track": track,
        "citations": work.get("cited_by_count"),
        "citation_source": "OpenAlex",
        "citation_checked_at": dt.date.today().isoformat(),
        "is_retracted": bool(work.get("is_retracted")),
        "abstract": inverted_abstract(work.get("abstract_inverted_index")),
    }


def fetch_openalex(query: str, track: str, since: dt.date, per_query: int, mailto: str | None) -> list[dict[str, Any]]:
    today = dt.date.today()
    params = {
        "search": query,
        "filter": (
            f"from_publication_date:{since.isoformat()},"
            f"to_publication_date:{today.isoformat()},has_abstract:true,is_retracted:false"
        ),
        "sort": "publication_date:desc",
        "per_page": str(per_query),
    }
    if mailto:
        params["mailto"] = mailto
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "ResearchDaily/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return [openalex_to_candidate(work, track) for work in payload.get("results", [])]


def validate_review(review: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_REVIEW_FIELDS if review.get(field) in (None, "", [])]
    if missing:
        raise ValueError("review missing required fields: " + ", ".join(missing))
    if review.get("full_text_read") is not True:
        raise ValueError("full_text_read must be true; abstract-only reviews are forbidden")
    if not isinstance(review.get("contributions"), list) or len(review["contributions"]) < 1:
        raise ValueError("contributions must be a non-empty list")
    for score_name in ("quality_score", "relevance_score", "innovation_score"):
        score = float(review[score_name])
        if not 0 <= score <= 10:
            raise ValueError(f"{score_name} must be between 0 and 10")
    minutes = int(review["reading_minutes"])
    if not 2 <= minutes <= 20:
        raise ValueError("reading_minutes must be between 2 and 20")
    takeaway = str(review["plain_language_takeaway"]).strip()
    if len(takeaway) < 20:
        raise ValueError("plain_language_takeaway is too short to be useful")


def save_review(conn: sqlite3.Connection, review: dict[str, Any]) -> None:
    validate_review(review)
    paper = conn.execute("SELECT track FROM papers WHERE id = ?", (review["paper_id"],)).fetchone()
    if paper is None:
        raise ValueError(f"unknown paper_id: {review['paper_id']}")
    if paper["track"] == "ai_frontier":
        notes = str(review.get("reviewer_notes") or "")
        if not re.search(r"(?m)^peer_review_status:\s*unreviewed\s*$", notes) or not re.search(r"(?m)^version:\s*\S[^\n]*$", notes):
            raise ValueError("AI frontier review requires peer_review_status: unreviewed and version: in reviewer_notes")
    conn.execute(
        """
        INSERT INTO reviews (
            paper_id, full_text_read, full_text_url, access_method, read_at,
            plain_language_takeaway, problem, method, contributions_json, delta,
            evidence, limitations, why_read, sections_to_read, reading_minutes,
            quality_score, relevance_score, innovation_score, reviewer_notes, updated_at
        ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(paper_id) DO UPDATE SET
            full_text_url = excluded.full_text_url,
            access_method = excluded.access_method,
            read_at = excluded.read_at,
            plain_language_takeaway = excluded.plain_language_takeaway,
            problem = excluded.problem,
            method = excluded.method,
            contributions_json = excluded.contributions_json,
            delta = excluded.delta,
            evidence = excluded.evidence,
            limitations = excluded.limitations,
            why_read = excluded.why_read,
            sections_to_read = excluded.sections_to_read,
            reading_minutes = excluded.reading_minutes,
            quality_score = excluded.quality_score,
            relevance_score = excluded.relevance_score,
            innovation_score = excluded.innovation_score,
            reviewer_notes = excluded.reviewer_notes,
            updated_at = excluded.updated_at
        """,
        (
            review["paper_id"],
            review["full_text_url"],
            review["access_method"],
            review["read_at"],
            review["plain_language_takeaway"].strip(),
            review["problem"].strip(),
            review["method"].strip(),
            json.dumps(review["contributions"], ensure_ascii=False),
            review["delta"].strip(),
            review["evidence"].strip(),
            review["limitations"].strip(),
            review["why_read"].strip(),
            review["sections_to_read"].strip(),
            int(review["reading_minutes"]),
            float(review["quality_score"]),
            float(review["relevance_score"]),
            float(review["innovation_score"]),
            str(review.get("reviewer_notes") or "").strip(),
            now_iso(),
        ),
    )


def track_role(track: str, interests: dict[str, Any]) -> str:
    return interests.get("tracks", {}).get(track, {}).get("role", "adjacent")


def candidate_score(row: sqlite3.Row, interests: dict[str, Any]) -> float:
    weights = interests["ranking"]
    citations = max(int(row["citations"] or 0), 0)
    impact = min(10.0, math.log1p(citations) * 2.2)
    return (
        weights["relevance"] * row["relevance_score"]
        + weights["quality"] * row["quality_score"]
        + weights["innovation"] * row["innovation_score"]
        + weights["impact"] * impact
        + weights["venue"] * row["venue_score"]
    )


def eligible_rows(conn: sqlite3.Connection, interests: dict[str, Any]) -> list[sqlite3.Row]:
    min_quality = float(interests["brief"]["min_quality_score"])
    return list(
        conn.execute(
            """
            SELECT p.*, r.*
            FROM papers p JOIN reviews r ON r.paper_id = p.id
            LEFT JOIN recommendations rec ON rec.paper_id = p.id
            WHERE rec.paper_id IS NULL
              AND p.is_retracted = 0
              AND r.full_text_read = 1
              AND r.quality_score >= ?
            """,
            (min_quality,),
        )
    )


def committed_rows(conn: sqlite3.Connection, brief_date: str) -> list[tuple[str, sqlite3.Row]]:
    """Return a previously committed edition in its original order."""
    rows = conn.execute(
        """
        SELECT p.*, r.*, rec.section AS committed_section, rec.position AS committed_position
        FROM recommendations rec
        JOIN papers p ON p.id = rec.paper_id
        JOIN reviews r ON r.paper_id = p.id
        WHERE rec.brief_date = ?
        ORDER BY rec.position
        """,
        (brief_date,),
    ).fetchall()
    return [(str(row["committed_section"]), row) for row in rows]


def topic_family(row: sqlite3.Row) -> str:
    """Prefer the reviewer's explicit topic; retain a fallback for older reviews."""
    notes = row["reviewer_notes"] or ""
    explicit = re.search(r"(?:^|\n)topic:\s*([a-z0-9_-]+)", notes, re.I)
    if explicit:
        return explicit.group(1).lower()
    title = row["title"].lower()
    for topic, terms in {
        "health_monitoring": ("blood pressure", "hypertension", "physiological", "biomarker"),
        "accessibility": ("accessib", "assistive", "exoskeleton", "tongue"),
        "rf_sensing": ("wi-fi", "wifi", "radar", "radio frequency"),
        "personal_health_data": ("wearable data", "personal health"),
        "research_practice": ("research idea", "scientific idea", "researcher"),
        "robot_learning": ("robot learning", "manipulation", "tactile"),
    }.items():
        if any(term in title for term in terms):
            return topic
    return "paper:" + row["id"]


def select_rows(rows: list[sqlite3.Row], interests: dict[str, Any]) -> list[tuple[str, sqlite3.Row]]:
    pools: dict[str, list[sqlite3.Row]] = {role: [] for role in BRIEF_ROLES}
    for row in rows:
        role = track_role(row["track"], interests)
        pools.setdefault(role, []).append(row)
    for pool in pools.values():
        pool.sort(key=lambda row: (candidate_score(row, interests), row["publication_date"] or ""), reverse=True)

    brief = interests["brief"]
    quotas = interests["quotas"]
    selected: list[tuple[str, sqlite3.Row]] = []
    used_minutes = 0
    diversity = interests.get("diversity", {})

    def take(role: str, count: int) -> None:
        nonlocal used_minutes
        while count > 0 and pools.get(role):
            row = pools[role][0]
            minutes = int(row["reading_minutes"])
            topic = topic_family(row)
            if (sum(topic_family(item) == topic for _, item in selected) >= int(diversity.get("max_same_topic_per_brief", 2))
                or sum(r == role and topic_family(item) == topic for r, item in selected) >= int(diversity.get("max_same_topic_per_section", 1))):
                pools[role].pop(0)
                continue
            if len(selected) >= int(brief["max_items"]):
                return
            if used_minutes + minutes > int(brief["max_minutes"]):
                pools[role].pop(0)
                continue
            selected.append((role, pools[role].pop(0)))
            used_minutes += minutes
            count -= 1

    take("core", int(quotas["core_min"]))
    take("adjacent", int(quotas["adjacent_min"]))
    take("heavyweight", int(quotas["heavyweight_target"]))
    take("serendipity", int(quotas.get("serendipity_min", 1)))
    take("ai_frontier", int(quotas.get("ai_frontier_max", 0)))

    core_extra = max(0, int(quotas["core_max"]) - sum(1 for role, _ in selected if role == "core"))
    adjacent_extra = max(0, int(quotas["adjacent_max"]) - sum(1 for role, _ in selected if role == "adjacent"))
    while len(selected) < int(brief["max_items"]) and (core_extra or adjacent_extra):
        options: list[tuple[float, str]] = []
        if core_extra and pools["core"]:
            options.append((candidate_score(pools["core"][0], interests), "core"))
        if adjacent_extra and pools["adjacent"]:
            options.append((candidate_score(pools["adjacent"][0], interests), "adjacent"))
        if not options:
            break
        _, role = max(options)
        before = len(selected)
        take(role, 1)
        if role == "core":
            core_extra -= 1
        else:
            adjacent_extra -= 1
        if len(selected) == before and not pools[role]:
            continue

    take("heavyweight", max(0, int(quotas.get("heavyweight_max", 2)) - sum(r == "heavyweight" for r, _ in selected)))
    take("serendipity", max(0, int(quotas["serendipity_max"]) - sum(r == "serendipity" for r, _ in selected)))
    return selected


def format_paper(index: int, role: str, row: sqlite3.Row) -> str:
    authors = "、".join(json.loads(row["authors_json"]))
    contributions = "\n".join(f"  - {item}" for item in json.loads(row["contributions_json"]))
    metric = "暂无可核验引用指标"
    if row["citations"] is not None:
        metric = f"{row['citation_source'] or '来源未注明'} 引用数 {row['citations']}（查询于 {row['citation_checked_at'] or '日期未记录'}）"
    peer_status = "预印本/未确认同行评审" if (row["work_type"] or "").lower() in {"preprint", "posted-content"} else "正式发表或会议收录；早报已核对全文"
    frontier_status = "\n- **状态：** 前沿预印本／技术报告，尚未经同行评审。" if role == "ai_frontier" else ""
    if role == "ai_frontier":
        version = re.search(r"(?m)^version:\s*(.+)$", row["reviewer_notes"] or "")
        frontier_status += f" 本次阅读版本：{version.group(1) if version else '未记录'}。"
    return f"""### {index}. {row['title']}

- **作者：** {authors}
- **平台与年份：** {row['venue'] or '平台待核验'}，{row['publication_year'] or '年份待核验'}
- **类型：** {row['work_type'] or '未注明'}；{peer_status}
- **链接：** [论文页面]({row['source_url']}) · [本次阅读全文入口]({row['full_text_url']})
- **影响力指标：** {metric}
- **阅读时间：** 约 {row['reading_minutes']} 分钟{frontier_status}

**说人话：** {row['plain_language_takeaway']}

**它在解决什么：** {row['problem']}

**怎么做的：** {row['method']}

**主要贡献：**
{contributions}

**相较以往工作的 delta：** {row['delta']}

**证据够不够：** {row['evidence']}

**局限：** {row['limitations']}

**为什么值得你读：** {row['why_read']}

**优先看：** {row['sections_to_read']}
"""


def render_brief(selected: list[tuple[str, sqlite3.Row]], brief_date: str, interests: dict[str, Any]) -> str:
    total_minutes = sum(int(row["reading_minutes"]) for _, row in selected)
    role_names = {
        "core": "核心兴趣",
        "adjacent": "邻近领域",
        "heavyweight": "重量级内容",
        "serendipity": "其他领域",
        "ai_frontier": "AI 新动向",
    }
    lines = [
        f"# 学术早报 · {brief_date}",
        "",
        f"今日共 {len(selected)} 篇，预计 {total_minutes} 分钟。所有入选文章均已阅读全文；系统不会用摘要级总结补位。",
        "",
    ]
    if selected:
        top = sorted(selected, key=lambda pair: candidate_score(pair[1], interests), reverse=True)[:2]
        lines.extend(["## 如果今天只能读两篇", ""])
        for _, row in top:
            lines.append(f"- [{row['title']}]({row['source_url']})：{row['plain_language_takeaway']}")
        lines.append("")
    for role in BRIEF_ROLES:
        group = [row for selected_role, row in selected if selected_role == role]
        lines.extend([f"## {role_names[role]}", ""])
        if not group:
            empty_note = ("可选栏目：本期尚无完成全文核验且达到质量门槛的入选候选；不计入原四栏缺口。"
                          if role == "ai_frontier" else "本期缺项：尚无满足全文、质量及主题多样性要求的已审阅候选。")
            lines.extend([empty_note, ""])
        for row in group:
            lines.append(format_paper(selected.index((role, row)) + 1, role, row))
    missing = []
    quotas = interests["quotas"]
    if sum(1 for role, _ in selected if role == "core") < int(quotas["core_min"]):
        missing.append("核心兴趣")
    if sum(1 for role, _ in selected if role == "adjacent") < int(quotas["adjacent_min"]):
        missing.append("邻近领域")
    if sum(1 for role, _ in selected if role == "heavyweight") < int(quotas["heavyweight_target"]):
        missing.append("重量级内容")
    if sum(1 for role, _ in selected if role == "serendipity") < int(quotas.get("serendipity_min", 1)):
        missing.append("其他领域")
    if missing:
        lines.extend([
            "## 今日缺口",
            "",
            "以下栏目没有足够的全文已读、高质量且未推荐过的候选，因此没有用低质量文章凑数：" + "、".join(missing) + "。",
            "",
        ])
    lines.extend([
        "---",
        "指标会随时间变化；引用数均附来源与查询日期。论文未保存到本地，本早报只保存元数据、阅读入口和原创总结。",
        "",
    ])
    return "\n".join(lines)


def render_site_archive_page(
    selected: list[tuple[str, sqlite3.Row]], brief_date: str, interests: dict[str, Any]
) -> str:
    """Render one immutable, dated web edition from committed database records."""
    role_names = {
        "core": "核心兴趣",
        "adjacent": "邻近领域",
        "heavyweight": "重量级内容",
        "serendipity": "其他领域",
        "ai_frontier": "AI 新动向",
    }
    role_labels = {
        "core": "PRIMARY SIGNAL",
        "adjacent": "ADJACENT FIELD",
        "heavyweight": "LANDMARK READ",
        "serendipity": "SERENDIPITY",
        "ai_frontier": "AI FRONTIER · PREPRINT",
    }
    role_classes = {
        "core": "core",
        "adjacent": "adjacent",
        "heavyweight": "landmark",
        "serendipity": "random",
        "ai_frontier": "ai-frontier",
    }
    total_minutes = sum(int(row["reading_minutes"]) for _, row in selected)
    top = sorted(selected, key=lambda pair: candidate_score(pair[1], interests), reverse=True)[:2]
    quotas = interests["quotas"]
    minimums = {"core": int(quotas["core_min"]), "adjacent": int(quotas["adjacent_min"]), "heavyweight": int(quotas["heavyweight_target"]), "serendipity": int(quotas.get("serendipity_min", 1))}
    maximums = {"core": int(quotas["core_max"]), "adjacent": int(quotas["adjacent_max"]), "heavyweight": int(quotas.get("heavyweight_max", 2)), "serendipity": int(quotas["serendipity_max"])}
    minimums["ai_frontier"] = 0
    maximums["ai_frontier"] = int(quotas.get("ai_frontier_max", 0))

    def esc(value: Any) -> str:
        return html.escape(str(value or ""), quote=True)

    def paper_card(index: int, role: str, row: sqlite3.Row) -> str:
        authors = "、".join(json.loads(row["authors_json"]))
        contributions = "".join(
            f"<li><span>{number:02d}</span><p>{esc(item)}</p></li>"
            for number, item in enumerate(json.loads(row["contributions_json"]), start=1)
        )
        metric = "暂无可核验引用指标"
        if row["citations"] is not None:
            metric = f"{row['citation_source'] or '来源未注明'} 引用 {row['citations']} · {row['citation_checked_at'] or '日期未记录'}"
        frontier_badge = ""
        if role == "ai_frontier":
            version = re.search(r"(?m)^version:\s*(.+)$", row["reviewer_notes"] or "")
            frontier_badge = '<p class="access-note">前沿预印本／技术报告 · 尚未经同行评审 · 阅读版本：' + esc(version.group(1) if version else "未记录") + '</p>'
        return f"""
        <article class="paper">
          <div class="paper-index">{index:02d}</div>
          <div class="paper-main">
            <div class="meta"><span>{esc(row['venue'])} · {esc(row['publication_year'])}</span><span>{row['reading_minutes']} MIN</span><span>{esc(metric)}</span></div>
            <h3>{esc(row['title'])}</h3>
            <p class="authors">{esc(authors)}</p>
            {frontier_badge}
            <div class="plain"><small>说人话</small><p>{esc(row['plain_language_takeaway'])}</p></div>
            <details><summary>展开完整精读笔记 <span>+</span></summary>
              <div class="review-sheet">
                <div class="review-kicker"><span>FULL-TEXT NOTES</span><p>来自方法、结果、讨论与局限部分的全文核验，不是摘要改写。</p></div>
                <div class="review-pair">
                  <section class="review-block"><b>01</b><div><h4>研究问题</h4><p>{esc(row['problem'])}</p></div></section>
                  <section class="review-block"><b>02</b><div><h4>方法与样本</h4><p>{esc(row['method'])}</p></div></section>
                </div>
                <section class="review-contributions"><div class="review-title"><b>03</b><h4>主要贡献</h4><span>作者实际交付了什么</span></div><ol>{contributions}</ol></section>
                <section class="review-delta"><div class="review-title"><b>04</b><h4>相较以往的 delta</h4><span>过去做法 → 本文改变 → 仍需付出的代价</span></div><p>{esc(row['delta'])}</p></section>
                <div class="review-pair judgement">
                  <section class="review-block evidence"><b>05</b><div><h4>证据够不够</h4><p>{esc(row['evidence'])}</p></div></section>
                  <section class="review-block limitations"><b>06</b><div><h4>局限与不可外推之处</h4><p>{esc(row['limitations'])}</p></div></section>
                </div>
                <div class="review-bottom">
                  <section><span>WHY READ</span><h4>为什么值得你读</h4><p>{esc(row['why_read'])}</p></section>
                  <section><span>READING PATH</span><h4>如果打开原文，优先看这里</h4><p>{esc(row['sections_to_read'])}</p></section>
                </div>
              </div>
            </details>
            <div class="paper-links"><a href="{esc(row['source_url'])}" target="_blank" rel="noreferrer">论文页面 ↗</a><a href="{esc(row['full_text_url'])}" target="_blank" rel="noreferrer">阅读全文 ↗</a></div>
          </div>
          <aside class="why"><span>{role_labels[role]}</span><p>{esc(row['why_read'])}</p></aside>
        </article>"""

    priority = "".join(
        f'<a href="#paper-{row["id"]}"><span>{index:02d}</span><strong>{esc(row["plain_language_takeaway"])}</strong><i>{row["reading_minutes"]} min ↗</i></a>'
        for index, (_, row) in enumerate(top, start=1)
    )
    sections: list[str] = []
    for section_index, role in enumerate(BRIEF_ROLES, start=1):
        group = [(index, row) for index, (selected_role, row) in enumerate(selected, start=1) if selected_role == role]
        cards = []
        if not group:
            empty_note = ("可选栏目：本期尚无完成全文核验且达到质量门槛的入选候选；不计入原四栏缺口。"
                          if role == "ai_frontier" else "本期缺项：尚无满足全文、质量及主题多样性要求的已审阅候选。")
            cards.append(f'<p class="dek">{empty_note}</p>')
        for index, row in group:
            card = paper_card(index, role, row).replace('<article class="paper">', f'<article class="paper" id="paper-{row["id"]}">', 1)
            cards.append(card)
        sections.append(
            f'<section class="paper-section {role_classes[role]}" id="{role}"><header class="section-head"><div><span class="section-no">{section_index:02d}</span><p>{role_labels[role]}</p></div><h2>{role_names[role]}</h2><p>已收录 {len(group)} 篇 / 目标 {minimums[role]}–{maximums[role]} 篇。' + (f'距最低配额仍缺 {minimums[role] - len(group)} 篇。' if len(group) < minimums[role] else '本栏最低配额已满足。') + f'</p></header>{"".join(cards)}</section>'
        )

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Research Daily · {brief_date}</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Noto+Sans+SC:wght@400;500;600;700;900&family=Noto+Serif+SC:wght@600;700;900&display=swap" rel="stylesheet"><link rel="stylesheet" href="../../styles.css"><style>.paper-section.ai-frontier{{--accent:#126871}}</style></head>
<body><header class="masthead"><a class="brand" href="../"><span class="brand-mark">RD</span><span><strong>RESEARCH DAILY</strong><small>FULL-TEXT REVIEWED</small></span></a><div class="issue"><a class="archive-link" href="../">综合目录</a>&nbsp;&nbsp;·&nbsp;&nbsp;{brief_date}</div></header>
<main><section class="hero archive-hero"><div class="hero-copy"><p class="eyebrow">PERMANENT DAILY EDITION</p><h1>{brief_date}<br><em>学术早报</em></h1><p class="dek">共 {len(selected)} 篇，建议阅读 {total_minutes} 分钟。此页面按日期永久保存，后续早报不会覆盖本期内容。</p><div class="hero-actions"><a class="primary" href="#core">开始阅读 <span>↓</span></a><a class="ghost archive-button" href="../">查看全部日期</a></div></div><aside class="reading-map"><div class="map-head"><span>ARCHIVED EDITION</span><strong>{total_minutes}<span>MIN</span></strong></div><p class="archive-count">{len(selected)} 篇全文核验论文<br>推荐记录已写入永久去重账本</p></aside></section>
<section class="priority"><div class="priority-label"><span>IF YOU ONLY READ TWO</span><b>只读两篇</b></div>{priority}</section>{''.join(sections)}</main>
<footer><div><span class="brand-mark">RD</span><p><strong>Research Daily</strong><br>读全文，讲人话，不重复。</p></div><p>{len(selected)} PAPERS · {total_minutes} MINUTES<br>ARCHIVED · {brief_date}</p><a href="#top">BACK TO TOP ↑</a></footer><script src="../../app.js"></script><script src="../../feedback.js"></script></body></html>"""


def render_site_archive_index(editions: list[sqlite3.Row]) -> str:
    cards = "".join(
        f'<a class="archive-card" href="./{html.escape(str(row["brief_date"]))}/"><span>{html.escape(str(row["brief_date"]))}</span><strong>{row["item_count"]} 篇论文</strong><b>{row["total_minutes"]} min</b><i>打开本期 →</i></a>'
        for row in editions
    )
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Research Daily · 综合目录</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Noto+Sans+SC:wght@400;500;600;700;900&family=Noto+Serif+SC:wght@600;700;900&display=swap" rel="stylesheet"><link rel="stylesheet" href="../styles.css"></head><body><header class="masthead"><a class="brand" href="./"><span class="brand-mark">RD</span><span><strong>RESEARCH DAILY</strong><small>FULL-TEXT REVIEWED</small></span></a><div class="issue">PERMANENT ARCHIVE</div></header><main class="archive-home"><p class="eyebrow">EVERY EDITION, KEPT</p><h1>综合<br><em>早报目录</em></h1><p class="dek">每天的报告都按日期独立保存。旧内容不会被新一期覆盖，已经推荐过的论文也不会重新占用每日名额。</p><div class="archive-grid">{cards}</div></main><footer><div><span class="brand-mark">RD</span><p><strong>Research Daily</strong><br>读全文，讲人话，不重复。</p></div><p>{len(editions)} ARCHIVED EDITION{'S' if len(editions) != 1 else ''}</p><a href="./">返回目录顶部 ↑</a></footer></body></html>"""


def command_init(args: argparse.Namespace) -> None:
    with connect(args.db) as conn:
        counts = {
            "papers": conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0],
            "reviews": conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0],
            "recommendations": conn.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0],
        }
    print(json.dumps({"database": str(args.db), **counts}, ensure_ascii=False, indent=2))


def command_import(args: argparse.Namespace) -> None:
    records = read_json_records(args.path)
    sources = load_config(SOURCES_PATH)
    with connect(args.db) as conn:
        ids = [upsert_candidate(conn, item, sources) for item in records]
        conn.commit()
    print(json.dumps({"imported": len(records), "paper_ids": ids}, ensure_ascii=False, indent=2))


def command_collect(args: argparse.Namespace) -> None:
    discovery = load_config(DISCOVERY_PATH)
    if not discovery.get("legacy_keyword_collection_enabled", False) and not getattr(args, "allow_keyword_fallback", False):
        raise ValueError("Default discovery is catalog-first: run discovery-plan and use its skill. "
                         "Use --allow-keyword-fallback only for a documented supplementary search.")
    if not discovery.get("legacy_keyword_collection_enabled", False) and not (args.query and args.track):
        raise ValueError("A supplementary keyword search requires --query and --track for its actual gap")
    sources = load_config(SOURCES_PATH)
    interests = load_config(INTERESTS_PATH)
    since = dt.date.today() - dt.timedelta(days=args.days)
    all_records: list[dict[str, Any]] = []
    searches = ([{"query": args.query, "track": args.track}] if args.query and args.track
                else sources.get("searches", []))
    for search in searches:
        records = fetch_openalex(search["query"], search["track"], since, args.per_query, args.mailto)
        all_records.extend(records)
    filtered_records = [
        record
        for record in all_records
        if record.get("title")
        and record.get("authors")
        and passes_discovery_prefilter(record, sources, interests, dt.date.today())
    ]
    with connect(args.db) as conn:
        ids = [upsert_candidate(conn, record, sources) for record in filtered_records]
        conn.commit()
    print(
        json.dumps(
            {
                "fetched": len(all_records),
                "passed_discovery_filter": len(filtered_records),
                "upserted": len(ids),
                "since": since.isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def command_candidates(args: argparse.Namespace) -> None:
    with connect(args.db) as conn:
        rows = conn.execute(
            """
            SELECT p.*, CASE WHEN r.paper_id IS NULL THEN 0 ELSE 1 END AS reviewed,
                   CASE WHEN rec.paper_id IS NULL THEN 0 ELSE 1 END AS recommended
            FROM papers p
            LEFT JOIN reviews r ON r.paper_id = p.id
            LEFT JOIN recommendations rec ON rec.paper_id = p.id
            WHERE (? IS NULL OR p.track = ?)
            ORDER BY p.publication_date DESC, p.created_at DESC
            LIMIT ?
            """,
            (args.track, args.track, args.limit),
        )
        output = [
            {
                "paper_id": row["id"],
                "title": row["title"],
                "authors": json.loads(row["authors_json"]),
                "date": row["publication_date"],
                "venue": row["venue"],
                "track": row["track"],
                "url": row["source_url"],
                "pdf_url": row["pdf_url"],
                "citations": row["citations"],
                "reviewed": bool(row["reviewed"]),
                "recommended": bool(row["recommended"]),
            }
            for row in rows
        ]
    print(json.dumps(output, ensure_ascii=False, indent=2))


def save_discovery(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    """Persist current checkpoints/annotations; callers commit the batch atomically."""
    timestamp = now_iso()
    for source in payload.get("sources", []):
        if not source.get("source_key") or not source.get("url"):
            raise ValueError("discovery source requires source_key and url")
        if not isinstance(source.get("complete"), bool):
            raise ValueError("source complete must be a JSON boolean")
        conn.execute(
            "INSERT INTO discovery_sources VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(source_key) DO UPDATE SET url=excluded.url, cursor=excluded.cursor, "
            "complete=excluded.complete, notes=excluded.notes, checked_at=excluded.checked_at",
            (source["source_key"], source["url"], source.get("cursor", ""), int(source["complete"]),
             source.get("notes", ""), timestamp),
        )
    for decision in payload.get("decisions", []):
        for field in ("paper_id", "source_key", "topic", "status", "reason"):
            if not isinstance(decision.get(field), str) or not decision[field].strip():
                raise ValueError(f"discovery decision requires {field}")
        if decision["status"] not in {"shortlist", "defer", "reject", "access_blocked"}:
            raise ValueError("invalid discovery status")
        retry = decision.get("retry_after")
        if retry is not None:
            dt.date.fromisoformat(retry)
        conn.execute(
            "INSERT INTO discovery_decisions VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(paper_id, source_key) DO UPDATE SET topic=excluded.topic, status=excluded.status, "
            "reason=excluded.reason, retry_after=excluded.retry_after, updated_at=excluded.updated_at",
            (decision["paper_id"], decision["source_key"], decision["topic"], decision["status"],
             decision["reason"], retry, timestamp),
        )


def command_discovery_record(args: argparse.Namespace) -> None:
    payload = load_config(args.path)
    if not isinstance(payload, dict):
        raise ValueError("discovery state must be a JSON object")
    with connect(args.db) as conn:
        save_discovery(conn, payload)
    print(json.dumps({"sources_saved": len(payload.get("sources", [])),
                      "decisions_saved": len(payload.get("decisions", []))}))


def command_discovery_plan(args: argparse.Namespace) -> None:
    policy = load_config(DISCOVERY_PATH)
    skill = (ROOT / policy["skill"]).resolve()
    if not skill.is_file():
        raise ValueError(f"configured discovery skill not found: {skill}")
    with connect(args.db) as conn:
        sources = [dict(row) for row in conn.execute("SELECT * FROM discovery_sources ORDER BY checked_at")]
        counts = {row["status"]: row["n"] for row in conn.execute(
            "SELECT status, COUNT(*) AS n FROM discovery_decisions GROUP BY status")}
        result = {"skill": str(skill), "policy": policy, "database": str(args.db),
                  "sources": sources, "annotation_counts": counts}
        if args.source_key:
            result["decisions"] = [dict(row) for row in conn.execute(
                "SELECT * FROM discovery_decisions WHERE source_key = ? ORDER BY updated_at", (args.source_key,))]
    print(json.dumps(result, ensure_ascii=False, indent=2))


def command_review(args: argparse.Namespace) -> None:
    reviews = read_json_records(args.path)
    with connect(args.db) as conn:
        for review in reviews:
            save_review(conn, review)
        conn.commit()
    print(json.dumps({"reviews_saved": len(reviews)}, ensure_ascii=False, indent=2))


def command_generate(args: argparse.Namespace) -> None:
    interests = load_config(INTERESTS_PATH)
    with connect(args.db) as conn:
        output_path = args.output or ROOT / "briefs" / f"{args.date}.md"
        existing = committed_rows(conn, args.date)
        reused = bool(existing)
        selected = existing or select_rows(eligible_rows(conn, interests), interests)
        if not (reused and output_path.exists()):
            content = render_brief(selected, args.date, interests)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
        if args.commit and not existing:
            timestamp = now_iso()
            for position, (role, row) in enumerate(selected, start=1):
                conn.execute(
                    "INSERT INTO recommendations (brief_date, paper_id, section, position, created_at) VALUES (?, ?, ?, ?, ?)",
                    (args.date, row["id"], role, position, timestamp),
                )
            conn.commit()
    print(
        json.dumps(
            {
                "output": str(output_path),
                "items": len(selected),
                "committed": bool(args.commit or existing),
                "reused_existing_edition": reused,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def command_export_site(args: argparse.Namespace) -> None:
    interests = load_config(INTERESTS_PATH)
    with connect(args.db) as conn:
        selected = committed_rows(conn, args.date)
        if not selected:
            raise ValueError(f"no committed brief for date: {args.date}")
        editions = conn.execute(
            """
            SELECT rec.brief_date, COUNT(*) AS item_count, SUM(r.reading_minutes) AS total_minutes
            FROM recommendations rec
            JOIN reviews r ON r.paper_id = rec.paper_id
            GROUP BY rec.brief_date
            ORDER BY rec.brief_date DESC
            """
        ).fetchall()

    target = args.site_dist / "archive" / args.date / "index.html"
    reused = target.exists() and not args.replace
    if not reused:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_site_archive_page(selected, args.date, interests), encoding="utf-8")
    archive_index = args.site_dist / "archive" / "index.html"
    archive_index.parent.mkdir(parents=True, exist_ok=True)
    archive_index.write_text(render_site_archive_index(editions), encoding="utf-8")
    print(
        json.dumps(
            {
                "edition": str(target),
                "archive_index": str(archive_index),
                "items": len(selected),
                "reused_existing_archive": reused,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def command_feedback(args: argparse.Namespace) -> None:
    with connect(args.db) as conn:
        if args.paper_id and conn.execute("SELECT 1 FROM papers WHERE id = ?", (args.paper_id,)).fetchone() is None:
            raise ValueError(f"unknown paper_id: {args.paper_id}")
        conn.execute(
            "INSERT INTO feedback (paper_id, value, note, created_at) VALUES (?, ?, ?, ?)",
            (args.paper_id, args.value, args.note or "", now_iso()),
        )
        conn.commit()
    print(json.dumps({"saved": True}, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create the database schema and show counts")
    init.set_defaults(func=command_init)

    import_cmd = sub.add_parser("import-candidates", help="Import candidate JSON or JSONL")
    import_cmd.add_argument("path", type=Path)
    import_cmd.set_defaults(func=command_import)

    plan = sub.add_parser("discovery-plan", help="Resolve the discovery skill and show saved catalog progress")
    plan.add_argument("--source-key")
    plan.set_defaults(func=command_discovery_plan)

    discovery_record = sub.add_parser("record-discovery", help="Save catalog checkpoints and screening annotations")
    discovery_record.add_argument("path", type=Path)
    discovery_record.set_defaults(func=command_discovery_record)

    collect = sub.add_parser("collect-openalex", help="Optional supplementary keyword collection, not the default route")
    collect.add_argument("--days", type=int, default=45)
    collect.add_argument("--per-query", type=int, default=25)
    collect.add_argument("--mailto")
    collect.add_argument("--allow-keyword-fallback", action="store_true")
    collect.add_argument("--query", help="Gap-specific supplementary query")
    collect.add_argument("--track", choices=list(load_config(INTERESTS_PATH)["tracks"]))
    collect.set_defaults(func=command_collect)

    candidates = sub.add_parser("list-candidates", help="List candidates for full-text review")
    candidates.add_argument("--track")
    candidates.add_argument("--limit", type=int, default=50)
    candidates.set_defaults(func=command_candidates)

    review = sub.add_parser("record-review", help="Validate and store a full-text review JSON")
    review.add_argument("path", type=Path)
    review.set_defaults(func=command_review)

    generate = sub.add_parser("generate", help="Render a brief from eligible reviewed papers")
    generate.add_argument("--date", default=dt.date.today().isoformat())
    generate.add_argument("--output", type=Path)
    generate.add_argument("--commit", action="store_true", help="Permanently mark selected papers as recommended")
    generate.set_defaults(func=command_generate)

    export_site = sub.add_parser("export-site", help="Create an immutable dated web edition and refresh the archive index")
    export_site.add_argument("--date", default=dt.date.today().isoformat())
    export_site.add_argument("--site-dist", type=Path, default=SITE_DIST)
    export_site.add_argument("--replace", action="store_true", help="Replace an existing dated web edition")
    export_site.set_defaults(func=command_export_site)

    feedback = sub.add_parser("feedback", help="Store reader feedback")
    feedback.add_argument("value", choices=["read", "valuable", "skip", "more", "less", "save"])
    feedback.add_argument("--paper-id")
    feedback.add_argument("--note")
    feedback.set_defaults(func=command_feedback)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

