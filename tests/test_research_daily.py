import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("research_daily", ROOT / "scripts" / "research_daily.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ResearchDailyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Path(self.tempdir.name) / "test.sqlite"
        self.conn = MODULE.connect(self.db)
        self.sources = MODULE.load_config(MODULE.SOURCES_PATH)
        self.interests = MODULE.load_config(MODULE.INTERESTS_PATH)

    def tearDown(self):
        self.conn.close()
        self.tempdir.cleanup()

    def candidate(self, title="A Useful Sensing System", doi="10.1000/example", track="hci_ubicomp_sensing"):
        return {
            "title": title,
            "authors": ["Ada Researcher", "Bo Scientist"],
            "publication_year": 2026,
            "publication_date": "2026-11-01",
            "venue": "CHI",
            "work_type": "proceedings-article",
            "doi": doi,
            "source_url": f"https://doi.org/{doi}",
            "source_name": "test",
            "track": track,
            "citations": 3,
            "citation_source": "OpenAlex",
            "citation_checked_at": "2026-11-10",
        }

    def review(self, paper_id, quality=8.0):
        return {
            "paper_id": paper_id,
            "full_text_read": True,
            "full_text_url": "https://example.org/full-text",
            "access_method": "open_access",
            "read_at": "2026-11-10T08:00:00+00:00",
            "plain_language_takeaway": "这个系统把原来只能在实验室完成的感知任务带到了真实日常环境。",
            "problem": "现有方法依赖受控环境。",
            "method": "作者进行了系统构建和真实场景用户研究。",
            "contributions": ["提出新方法", "完成真实部署"],
            "delta": "过去只在实验室验证；本文首次进行长期真实部署，但设备种类仍有限。",
            "evidence": "包含基线比较和消融实验，证据总体充分。",
            "limitations": "样本来自单一地区。",
            "why_read": "与移动感知和真实部署直接相关。",
            "sections_to_read": "图 2、方法第 3 节、实验第 5 节。",
            "reading_minutes": 6,
            "quality_score": quality,
            "relevance_score": 9.0,
            "innovation_score": 8.0,
        }

    def test_doi_deduplicates(self):
        first = MODULE.upsert_candidate(self.conn, self.candidate(), self.sources)
        second_item = self.candidate(title="Changed Capitalization", doi="https://doi.org/10.1000/EXAMPLE")
        second = MODULE.upsert_candidate(self.conn, second_item, self.sources)
        self.conn.commit()
        self.assertEqual(first, second)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0], 1)

    def test_discovery_resumes_source_without_duplicate_annotations(self):
        pid = MODULE.upsert_candidate(self.conn, self.candidate(), self.sources)
        payload = {"sources": [{"source_key": "chi:2026", "url": "https://example.org/list",
                                "cursor": "page2", "complete": False}],
                   "decisions": [{"paper_id": pid, "source_key": "chi:2026", "topic": "interaction",
                                  "status": "defer", "reason": "Check later", "retry_after": "2026-11-20"}]}
        MODULE.save_discovery(self.conn, payload)
        MODULE.save_discovery(self.conn, payload)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM discovery_decisions").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT cursor FROM discovery_sources").fetchone()[0], "page2")
        payload["sources"][0].update(cursor="", complete=True)
        payload["decisions"][0].update(status="shortlist", reason="Read next", retry_after=None)
        MODULE.save_discovery(self.conn, payload)
        self.assertEqual(self.conn.execute("SELECT complete FROM discovery_sources").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT status FROM discovery_decisions").fetchone()[0], "shortlist")
        # Initial screening must never make an article eligible without a full-text review.
        self.assertEqual(MODULE.eligible_rows(self.conn, self.interests), [])

    def test_discovery_invalid_batch_rolls_back(self):
        self.conn.commit()
        with self.assertRaises(ValueError):
            with self.conn:
                MODULE.save_discovery(self.conn, {
                    "sources": [{"source_key": "new", "url": "https://example.org", "complete": False}],
                    "decisions": [{"paper_id": "unknown"}],
                })
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM discovery_sources").fetchone()[0], 0)

    def test_default_keyword_collector_stops_before_network_access(self):
        with self.assertRaisesRegex(ValueError, "catalog-first"):
            MODULE.command_collect(SimpleNamespace(allow_keyword_fallback=False))

    def test_minimum_sections_reserved_before_extras_and_topics_diverse(self):
        for i, (track, topic) in enumerate([
            ("hci_ubicomp_sensing", "rf"), ("hci_ubicomp_sensing", "rf"),
            ("hci_ubicomp_sensing", "interaction"), ("hci_ubicomp_sensing", "accessibility"),
            ("digital_health", "clinical"), ("digital_health", "health_ai"),
            ("broad_impact", "physics"), ("broad_impact", "biology"),
            ("serendipity", "ecology"),
        ]):
            pid = MODULE.upsert_candidate(self.conn, self.candidate(title=f"Paper {i}", doi=f"10.1000/{i}", track=track), self.sources)
            review = self.review(pid)
            review["reviewer_notes"] = f"topic: {topic}"
            review["reading_minutes"] = 3
            MODULE.save_review(self.conn, review)
        selected = MODULE.select_rows(MODULE.eligible_rows(self.conn, self.interests), self.interests)
        self.assertEqual([r for r, _ in selected], ["core", "core", "core", "adjacent", "adjacent", "heavyweight", "heavyweight", "serendipity"])
        self.assertEqual(len({MODULE.topic_family(row) for _, row in selected}), 8)

    def test_empty_sections_remain_visible(self):
        page = MODULE.render_site_archive_page([], "2026-11-11", self.interests)
        for role in MODULE.BRIEF_ROLES:
            self.assertIn(f'id="{role}"', page)

    def test_frontier_requires_status_and_version_and_remains_full_text_gated(self):
        pid = MODULE.upsert_candidate(self.conn, self.candidate(track="ai_frontier"), self.sources)
        review = self.review(pid)
        with self.assertRaisesRegex(ValueError, "peer_review_status"):
            MODULE.save_review(self.conn, review)
        review["reviewer_notes"] = "topic: agent_workflow\npeer_review_status: unreviewed\nversion: v2, 2026-11-10"
        review["full_text_read"] = False
        with self.assertRaisesRegex(ValueError, "abstract-only"):
            MODULE.save_review(self.conn, review)
        review["full_text_read"] = True
        MODULE.save_review(self.conn, review)
        selected = MODULE.select_rows(MODULE.eligible_rows(self.conn, self.interests), self.interests)
        self.assertEqual([role for role, _ in selected], ["ai_frontier"])
        page = MODULE.render_site_archive_page(selected, "2026-11-12", self.interests)
        markdown = MODULE.render_brief(selected, "2026-11-12", self.interests)
        for output in (page, markdown):
            self.assertIn("尚未经同行评审", output)
            self.assertIn("v2, 2026-11-10", output)

    def test_frontier_after_original_minimums_and_within_time_budget(self):
        tracks = ["hci_ubicomp_sensing", "hci_ubicomp_sensing", "digital_health",
                  "robotics_hri", "broad_impact", "broad_impact", "serendipity",
                  "ai_frontier", "hci_ubicomp_sensing"]
        for i, track in enumerate(tracks):
            pid = MODULE.upsert_candidate(self.conn, self.candidate(title=f"Item {i}", doi=f"10.1000/order{i}", track=track), self.sources)
            review = self.review(pid)
            review.update(reading_minutes=5, relevance_score=10-i/10,
                          reviewer_notes=f"topic: topic_{i}\npeer_review_status: unreviewed\nversion: v1")
            MODULE.save_review(self.conn, review)
        selected = MODULE.select_rows(MODULE.eligible_rows(self.conn, self.interests), self.interests)
        self.assertEqual([role for role, _ in selected][:9], ["core","core","core","adjacent","adjacent","heavyweight","heavyweight","serendipity","ai_frontier"])
        self.assertGreater(sum(row["reading_minutes"] for _, row in selected), 35)
        self.assertEqual(sum(role == "ai_frontier" for role, _ in selected), 1)

    def test_abstract_only_review_is_rejected(self):
        paper_id = MODULE.upsert_candidate(self.conn, self.candidate(), self.sources)
        review = self.review(paper_id)
        review["full_text_read"] = False
        with self.assertRaisesRegex(ValueError, "abstract-only reviews are forbidden"):
            MODULE.save_review(self.conn, review)

    def test_low_quality_is_not_selected(self):
        paper_id = MODULE.upsert_candidate(self.conn, self.candidate(), self.sources)
        MODULE.save_review(self.conn, self.review(paper_id, quality=5.0))
        self.conn.commit()
        rows = MODULE.eligible_rows(self.conn, self.interests)
        self.assertEqual(rows, [])

    def test_future_dated_discovery_record_is_rejected(self):
        candidate = self.candidate()
        candidate["publication_date"] = "2027-01-01"
        self.assertFalse(
            MODULE.passes_discovery_prefilter(
                candidate, self.sources, self.interests, MODULE.dt.date(2026, 11, 10)
            )
        )

    def test_search_noise_is_rejected_before_review(self):
        candidate = self.candidate(
            title="Language Teaching Strategies",
            doi="10.1000/noise",
            track="robotics_hri",
        )
        candidate["venue"] = "Unknown Outlet"
        candidate["abstract"] = "A classroom study of grammar instruction."
        self.assertFalse(
            MODULE.passes_discovery_prefilter(
                candidate, self.sources, self.interests, MODULE.dt.date(2026, 11, 10)
            )
        )

    def test_committed_recommendation_never_returns(self):
        paper_id = MODULE.upsert_candidate(self.conn, self.candidate(), self.sources)
        MODULE.save_review(self.conn, self.review(paper_id))
        self.conn.execute(
            "INSERT INTO recommendations VALUES (?, ?, ?, ?, ?)",
            ("2026-11-10", paper_id, "core", 1, MODULE.now_iso()),
        )
        self.conn.commit()
        self.assertEqual(MODULE.eligible_rows(self.conn, self.interests), [])

    def test_same_date_rerun_preserves_existing_brief(self):
        paper_id = MODULE.upsert_candidate(self.conn, self.candidate(), self.sources)
        MODULE.save_review(self.conn, self.review(paper_id))
        self.conn.execute(
            "INSERT INTO recommendations VALUES (?, ?, ?, ?, ?)",
            ("2026-11-10", paper_id, "core", 1, MODULE.now_iso()),
        )
        self.conn.commit()
        output = Path(self.tempdir.name) / "2026-11-10.md"
        output.write_text("original edition", encoding="utf-8")

        MODULE.command_generate(
            SimpleNamespace(db=self.db, date="2026-11-10", output=output, commit=True)
        )

        self.assertEqual(output.read_text(encoding="utf-8"), "original edition")
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM recommendations WHERE brief_date = ?", ("2026-11-10",)).fetchone()[0],
            1,
        )

    def test_export_site_keeps_existing_dated_page(self):
        paper_id = MODULE.upsert_candidate(self.conn, self.candidate(), self.sources)
        MODULE.save_review(self.conn, self.review(paper_id))
        self.conn.execute(
            "INSERT INTO recommendations VALUES (?, ?, ?, ?, ?)",
            ("2026-11-10", paper_id, "core", 1, MODULE.now_iso()),
        )
        self.conn.commit()
        site_dist = Path(self.tempdir.name) / "dist"
        target = site_dist / "archive" / "2026-11-10" / "index.html"
        target.parent.mkdir(parents=True)
        target.write_text("immutable edition", encoding="utf-8")

        MODULE.command_export_site(
            SimpleNamespace(db=self.db, date="2026-11-10", site_dist=site_dist, replace=False)
        )

        self.assertEqual(target.read_text(encoding="utf-8"), "immutable edition")
        self.assertTrue((site_dist / "archive" / "index.html").exists())


if __name__ == "__main__":
    unittest.main()

