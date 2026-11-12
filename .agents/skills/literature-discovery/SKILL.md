---
name: literature-discovery
description: Discover diverse ResearchDaily paper candidates incrementally from conference catalogs and high-impact journal updates, preserving screening annotations and source checkpoints. Use for candidate collection and screening, independently of full-text review and brief writing.
---

# Literature Discovery

Produce a diverse candidate handoff for ResearchDaily. This skill owns discovery and initial screening; the calling brief skill owns full-text scientific assessment, final selection and publication. Do not treat an abstract-based screening decision as a full-text review.

## Entry and boundaries

Run `python3 scripts/research_daily.py discovery-plan`, then read `config/discovery.json`, `config/sources.json` and the returned source/annotation state. The brief resolves this skill through the config path; a replacement must preserve the handoff in [references/handoff.md](references/handoff.md). Inspect recent recommendations and existing reviews in the ledger before spending new discovery effort.

Use the project's operational source groups, not bibliographic publication types:

- **Conference / specialist catalogs:** CHI, UIST, CSCW, IMWUT, TOCHI, PACMHCI, relevant ACM/IEEE publications and other specialist venues, including Health/AI/Robotics conferences. Process by edition, issue or online-publication batch as the source actually publishes. Preserve the real venue and publication type in metadata; TOCHI does not become a proceedings article.
- **High-impact journals:** Nature/Science flagships, their research journals, and comparable journals such as Cell, PNAS and The Lancet. Browse new contents and subjects; professional journals outside this scope use the specialist-catalog route. A publisher brand alone is not proof of quality or weight.

These discovery routes are independent of the final brief sections. A journal article can be adjacent, heavyweight or other-field; conference articles can also support exploration. Do not force a shared sensing theme across routes or sections.

Use `config/sources.json.journal_catalogs` as the explicit journal registry. Its subject labels guide rotation, not hard keyword filters. Spread primary journals across runs and sample rotating journals according to coverage/gaps; do not scan every journal every day or assume all Nature-branded articles have equal quality. Verify article type and peer-review status individually, especially Comments/Perspectives.

For the fifth brief section **AI 新动向**, read [references/ai-frontier.md](references/ai-frontier.md). It has a preprint discovery route and a 0–1 daily quota; the four established sections retain their minimums. “其他领域” continues to accept both conference and journal work from independent subjects.

## Discovery policy

1. Start from official accepted-paper lists, proceedings, issue contents or online-first lists. OpenAlex/Crossref/Semantic Scholar primarily enrich identity, citations and lawful full-text locations. Use venue-filtered indexing as a documented fallback if an official catalog is inaccessible. Do not silently fall back to yesterday's fixed keyword searches.
2. For conferences, index the latest available edition once and revisit only for additions/corrections. A conference release is a batch, not a daily stream. Begin with the recent publication window; if this leaves a shortage, widen to the configured fallback and then inspect the latest available edition even if older, explicitly flagging age. Do not label an old edition newly published. For specialist serials, follow issues/online-first batches and merge DOI repeats.
3. For high-impact journals, inspect new research and useful Reviews/Perspectives separately from news, corrections and other article types. Browse the whole new directory before applying subject priorities. Rotate life sciences, physical sciences, materials, environment and social/behavioral topics; use journal-specific subjects where available. Date-based ingestion needs an overlap plus ID deduplication so late-indexed items are not skipped.
4. Build a bounded initial-screen batch (default 24 new items total, configurable). Spread it across sources and sessions/subjects using recent coverage and category shortages. Reserve approximately the configured exploration fraction for under-covered subjects or seeded random picks among unscreened entries; record seed/selection basis. Topic assignment describes what an article studies, not what a fixed search phrase happens to match. Never claim catalog-wide coverage from a sampled batch.
   For heavyweight candidates, maintain two explicit lanes: `ai_robotics` and `hci_ubicomp_health`. Supply at least one promising candidate from each lane when available, plus a different-domain fallback. The journal name is not the domain label.
5. Title/abstract/session metadata can support initial screening. Record `shortlist`, `defer`, `reject` or `access_blocked`, a specific reason, topic and optional retry date. This is a decision about spending reading effort, not a quality score or a scientific summary. Prefer substantive problem/method variety; do not discard an unusual paper solely for low keyword overlap. Awards are useful signals, not admission gates.
6. Reuse prior decisions, reviews and recommendation IDs. Reconsider deferred/blocked articles when due, a version changes or access changes; reconsider topical rejections only when relevant criteria change. Do not repeatedly spend access attempts on unchanged blockers. A metadata correction is not a new paper. Reconcile suspected preprint/proceedings duplicates before handoff; identity heuristics are not infallible.
7. When a section is still short, use a targeted supplementary query derived from its actual gap, a cited neighboring work or a newly emerging idea. Record the query and reason. Existing `sources.json.searches` are legacy examples, not a daily checklist; `collect-openalex --allow-keyword-fallback` is explicit opt-in only.

## Save and hand off

Read [references/handoff.md](references/handoff.md) before saving. Import minimal candidates with `import-candidates`; persist source progress and initial decisions with `record-discovery`. Keep URLs, stable identifiers, small metadata, annotations and counts locally. Do not mirror whole publisher databases, PDFs or full abstracts. A resumable cursor must describe real progress; only mark a listing complete after all pages/entries in its stated scope were actually enumerated. Log partial access truthfully.

Return candidate IDs grouped by the four established sections plus optional AI 新动向, source/edition/issue and actual date, provisional topic, screening reason, lawful full-text leads, plus source/topic coverage and outstanding gaps. Pass promising candidates to the brief's full-text review; never set `full_text_read` here. Save counts and method provenance in `data/run-YYYY-MM-DD.json` so discovery cost and diversity can be inspected. Stop discovery within the calling run's remaining time budget and preserve partial progress.
