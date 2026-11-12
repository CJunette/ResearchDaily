---
name: academic-morning-brief
description: Prepare a personalized, full-text-verified academic morning brief with persistent deduplication, quality filtering, plain-language explanations, and a fixed reading-time budget. Use for daily paper discovery, screening, review, briefing, or feedback in the ResearchDaily project.
---

# Academic Morning Brief

Produce a trustworthy reading brief, not a list of search results. Use `scripts/research_daily.py` at the project root for state, deduplication, validation, and rendering.

Before writing, read the project skill `../personal-paper-reading/SKILL.md` and run `python3 scripts/reading_preferences.py profile`. Apply only established preferences within their stated scope; candidate observations from reading transcripts must not influence the brief. Keep direct current feedback distinct from inferred long-term traits. Record applied preference IDs in the daily run log. Missing/empty personal history means no learned style adjustment.

## Non-negotiable rules

- Read every selected paper in full. Abstracts, snippets, press coverage, and another model's summary do not count.
- Never record `full_text_read: true` unless the methods, results, discussion, and limitations were inspected. Read appendices when a central claim depends on them.
- If full text is inaccessible, try legitimate open versions and then ask the user to authorize or sign in to their institutional/publisher account. Do not bypass access controls. Do not recommend the paper until full text has been read.
- Do not download or retain PDFs unless the user asks. Store the access URL, metadata, and original review only.
- Apply the quality threshold to every section, including serendipity. Return fewer items instead of padding the brief.
- Once a paper has been committed to a brief, do not recommend it again. A materially changed version may appear only as a clearly labeled update outside the normal quota.
- Write the `plain_language_takeaway` in everyday Chinese: state what changed and why it matters without field jargon, inflated adjectives, or copying the abstract.
- Separate verified findings from author claims and your inference. Report metrics with source and retrieval date.

Read [references/editorial-policy.md](references/editorial-policy.md) before reviewing papers. For discovery, run `python3 scripts/research_daily.py discovery-plan` and read the skill at the returned `skill` path (configured in `config/discovery.json`). That module owns collection routes, incremental screening and its candidate handoff; do not duplicate or override its strategy here. Read [references/review-schema.md](references/review-schema.md) before recording reviews.

## Workflow

### Daily balance and runtime

- Always show five sections: 核心兴趣 (3–4, prioritize CHI/UIST/IMWUT/CSCW and related conferences), 邻近领域 (2–3), 重量级内容 (2–3, prioritize Nature/Science), 其他领域 (1–2, conference or journal), AI 新动向 (0–1, early AI ideas/applications). Reserve the increased original minimums 3+2+2+1, then consider AI 新动向 before other extras. The 30-minute figure is an approximate reader-facing estimate, not a hard selection cutoff; use it to report workload, and continue reviewing eligible papers when the edition runs longer. AI 新动向 requires full-text review and the same quality threshold, with explicit unreviewed status and actual manuscript version; follow the discovery skill's AI-frontier reference. Empty optional frontier does not make the original quotas incomplete.
- Search each section independently. Do not require health/AI/robotics, heavyweight science or other-field papers to share a sensing theme. Core papers should cover different problems (e.g. interaction techniques, social/accessibility, sensing systems); choose adjacent papers from different fields when possible.
- Every new review must put `topic: <specific_lowercase_topic>` on its own line in reviewer_notes. Use the same topic for near-duplicate research questions even across venues. The selector limits a topic to one paper per section and two per edition. These limits need an editorial semantic check; a venue change alone is not diversity.
- Inspect the previous seven editions and rotate overrepresented topics. Feedback affects ranking within this diversity budget, rather than concentrating the entire edition on one interest.
- Treat website feedback as open-ended text. Read each note first, then infer and summarize relevant signals such as positive interest, negative preference, questions, desired explanation depth, method/venue/topic preferences, and concerns about evidence. One note may contain several or conflicting signals. Do not require or infer meaning from a preselected UI category, and preserve uncertainty when the intent is ambiguous.
- Ask the discovery module for a shortlist covering all five sections, with at least three independent subject/session directions for core and two for each other section where available. Report actual gaps and publication dates; do not lower review quality. For AI 新动向, report the rolling-window dates inspected and use the newest eligible item rather than requiring same-day publication. Discovery routes are independent of final brief sections. In this project's source routing, IMWUT/TOCHI/PACMHCI and similar specialist publications follow the conference/specialist-catalog route; the journal route is reserved for Nature/Science families and comparable high-impact journals. Preserve actual publication types in metadata.
- Target 45 minutes of generation time, separate from reader time. Record wall-clock stage timestamps for discovery, full-text review, writing and publishing. Use bounded requests; after two failed access routes move to a replacement. Resolve the Node executable once at startup and open the Site in an empty scratch checkout, then reuse that checkout and opening result. Persist completed reviews immediately so retries can reuse them. At the time target, publish an edition with all five sections and precise original-quota shortages, labeling it incomplete when needed; do not claim full coverage.

1. Run `python3 scripts/research_daily.py init` and inspect the existing ledger.
2. Resolve and invoke the configured discovery skill. Reuse saved catalog checkpoints, initial screening annotations and existing full-text reviews. Receive candidate IDs, source/topic coverage and gaps through its documented handoff. `collect-openalex` is a documented supplementary fallback, not the daily entrypoint.
3. Use the handoff and `list-candidates` to choose a diverse, high-potential full-text shortlist. Confirm the publication identity, peer-review status, retraction/correction status, full author list, and venue. Initial discovery annotations never substitute for scientific quality assessment.
4. Open and read each full paper. If a login or subscription is needed, pause that paper and request the user's help in the browser. Continue with other accessible candidates while waiting when possible.
5. Write one structured review JSON per paper following the review schema, then call `record-review`. The validator must remain strict; do not weaken it to admit an abstract-only review.
6. Preview with `generate --date YYYY-MM-DD`. Inspect the output for factual support, accessible wording, category balance, and the reading-time budget.
7. Only after inspection, rerun with `--commit`. This permanently enters selected paper IDs in the recommendation ledger.

When the eligible pool cannot satisfy a quota, explain the shortage in the brief. Never lower the quality or full-text requirements silently.
