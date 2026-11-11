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

Read [references/editorial-policy.md](references/editorial-policy.md) before reviewing papers. Read [references/source-map.md](references/source-map.md) when collecting candidates or changing fields. Read [references/review-schema.md](references/review-schema.md) before recording reviews.

## Workflow

### Daily balance and runtime

- Always show four sections: 核心兴趣 (2–3, prioritize CHI/UIST/IMWUT/CSCW and related conferences), 邻近领域 (1–2), 重量级内容 (1–2, prioritize Nature/Science), 其他领域 (1–2). Reserve the minimum 2+1+1+1 before extras. Keep a 30-minute target and 35-minute reading ceiling; five to six papers normally fit better than nine.
- Search each section independently. Do not require health/AI/robotics, heavyweight science or other-field papers to share a sensing theme. Core papers should cover different problems (e.g. interaction techniques, social/accessibility, sensing systems); choose adjacent papers from different fields when possible.
- Every new review must put `topic: <specific_lowercase_topic>` on its own line in reviewer_notes. Use the same topic for near-duplicate research questions even across venues. The selector limits a topic to one paper per section and two per edition. These limits need an editorial semantic check; a venue change alone is not diversity.
- Inspect the previous seven editions and rotate overrepresented topics. Feedback affects ranking within this diversity budget, rather than concentrating the entire edition on one interest.
- Treat website feedback as open-ended text. Read each note first, then infer and summarize relevant signals such as positive interest, negative preference, questions, desired explanation depth, method/venue/topic preferences, and concerns about evidence. One note may contain several or conflicting signals. Do not require or infer meaning from a preselected UI category, and preserve uncertainty when the intent is ambiguous.
- First build a shortlist covering all four sections (at least three independent search directions for core and two for each other section). If a section is short, widen discovery from 45 to 180 days and label publication dates; do not lower review quality. Record attempted sources, candidates and rejection/access reasons per section.
- Target 45 minutes of generation time, separate from reader time. Record wall-clock stage timestamps for discovery, full-text review, writing and publishing. Use bounded requests; after two failed access routes move to a replacement. Resolve the Node executable once at startup and open the Site in an empty scratch checkout, then reuse that checkout and opening result. Persist completed reviews immediately so retries can reuse them. At the time target, publish a clearly labeled incomplete edition with all four sections and precise shortages; do not claim full coverage.

1. Run `python3 scripts/research_daily.py init` and inspect the existing ledger.
2. Collect recent candidates with `collect-openalex`, then supplement from the official venue and publisher sources in the source map. Import any additional candidates with `import-candidates`.
3. Use `list-candidates` to choose a diverse, high-potential shortlist. Confirm the publication identity, peer-review status, retraction/correction status, full author list, and venue.
4. Open and read each full paper. If a login or subscription is needed, pause that paper and request the user's help in the browser. Continue with other accessible candidates while waiting when possible.
5. Write one structured review JSON per paper following the review schema, then call `record-review`. The validator must remain strict; do not weaken it to admit an abstract-only review.
6. Preview with `generate --date YYYY-MM-DD`. Inspect the output for factual support, accessible wording, category balance, and the reading-time budget.
7. Only after inspection, rerun with `--commit`. This permanently enters selected paper IDs in the recommendation ledger.

When the eligible pool cannot satisfy a quota, explain the shortage in the brief. Never lower the quality or full-text requirements silently.
