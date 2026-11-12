# Discovery handoff and state

All paths/commands are relative to the ResearchDaily project root. Keep the discovery skill replaceable: read its entry path from `config/discovery.json`; use the existing candidate importer and the state interface below. Replacement skills can choose different collection methods without changing full-text review or rendering.

## Candidate interface

`python3 scripts/research_daily.py import-candidates path.json` accepts a JSON array (or JSONL) using existing fields:

```json
[{
  "title": "Actual paper title",
  "authors": ["Actual full author names"],
  "publication_year": 2026,
  "publication_date": "2026-10-01",
  "venue": "Actual venue name",
  "work_type": "journal-article",
  "doi": "10.example/actual-doi",
  "source_url": "https://publisher.example/actual-paper",
  "source_name": "Official issue contents",
  "track": "hci_ubicomp_sensing"
}]
```

Use actual verified metadata, not these placeholders. Date/DOI may be omitted when genuinely unavailable; never invent them. Tracks map to sections via `config/interests.json`: `hci_ubicomp_sensing` → core; `digital_health`, `robotics_hri`, `ai_vision` → adjacent; `broad_impact` → heavyweight; `serendipity` → other-field (conference or journal); `ai_frontier` → AI 新动向 (unreviewed early AI ideas/applications). Route by editorial purpose, not publisher alone. The importer returns canonical project paper IDs; save those in annotations. A shortlist is not proof of publication identity, full-text access or scientific quality; the reviewer must verify these.

## Progress and annotation interface

`python3 scripts/research_daily.py record-discovery path.json` accepts:

```json
{
  "sources": [{
    "source_key": "tochi:2026:issue-example",
    "url": "https://publisher.example/actual-contents",
    "cursor": "Next page or batch to inspect; empty when finished",
    "complete": false,
    "notes": "Inspected pages 1–2; page 3 remains"
  }],
  "decisions": [{
    "paper_id": "ID returned by import-candidates",
    "source_key": "tochi:2026:issue-example",
    "topic": "interaction_techniques",
    "status": "shortlist",
    "reason": "Potentially distinct interaction mechanism; read full paper next",
    "retry_after": null
  }]
}
```

Source keys identify a stable edition/issue/feed scope, not a mutable page number. Register the source before or in the same call as its decisions. State is stored in `data/papers.sqlite` alongside existing candidates/reviews. Updates replace the current checkpoint/annotation for the same key; past published editions are unaffected. State writes are transactional. `retry_after` is an optional ISO calendar date; statuses are `shortlist`, `defer`, `reject`, `access_blocked`. Annotations are provisional discovery judgements, distinct from full-text quality assessments.

`python3 scripts/research_daily.py discovery-plan` returns the configured skill path, policy, saved checkpoints, annotation counts and storage file. To inspect an individual source's decisions use `discovery-plan --source-key KEY`. Review existing candidates with `list-candidates` and inspect the ledger for reviews/recommendations before re-reading; the plan does not autonomously fetch, classify or select papers.

## Per-run record

Merge into the existing daily run log rather than overwrite other stages. Record the resolved skill path, sources/edition/issue scopes visited, cursor/partial status, IDs screened and chosen, subject/session coverage, counts by section, supplement queries and reasons, exploration seed/basis, access failures and remaining gaps. Counts describe the inspected scope only. Raw exports can be temporary; retained state should be minimal metadata and original annotations, not copied abstracts or PDFs.
