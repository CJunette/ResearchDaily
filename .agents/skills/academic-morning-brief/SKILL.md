---
name: academic-morning-brief
description: Prepare a personalized, full-text-verified academic morning brief with persistent deduplication, quality filtering, plain-language explanations, and a fixed reading-time budget. Use for daily paper discovery, screening, review, briefing, or feedback in the ResearchDaily project.
---

# Academic Morning Brief

Produce a trustworthy reading brief, not a list of search results. Use `scripts/research_daily.py` at the project root for state, deduplication, validation, and rendering.

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

1. Run `python3 scripts/research_daily.py init` and inspect the existing ledger.
2. Collect recent candidates with `collect-openalex`, then supplement from the official venue and publisher sources in the source map. Import any additional candidates with `import-candidates`.
3. Use `list-candidates` to choose a diverse, high-potential shortlist. Confirm the publication identity, peer-review status, retraction/correction status, full author list, and venue.
4. Open and read each full paper. If a login or subscription is needed, pause that paper and request the user's help in the browser. Continue with other accessible candidates while waiting when possible.
5. Write one structured review JSON per paper following the review schema, then call `record-review`. The validator must remain strict; do not weaken it to admit an abstract-only review.
6. Preview with `generate --date YYYY-MM-DD`. Inspect the output for factual support, accessible wording, category balance, and the reading-time budget.
7. Only after inspection, rerun with `--commit`. This permanently enters selected paper IDs in the recommendation ledger.

When the eligible pool cannot satisfy a quota, explain the shortage in the brief. Never lower the quality or full-text requirements silently.
