---
name: personal-paper-reading
description: Learn conservative, evidence-backed reading preferences from user-provided paper-reading conversations, and apply only established preferences to ResearchDaily briefs and paper explanations.
---

# Personal Paper Reading

Use this project-local skill when the user supplies co-reading records or when preparing a ResearchDaily brief. Its personal guidance comes from the private evidence ledger, not assumptions about the user's personality.

## Apply established preferences

Run `python3 scripts/reading_preferences.py profile` from the project root. Apply only the returned active preferences and only in their stated scope. An empty profile means no learned preference is available. Do not use candidate/ready hypotheses to change the brief. This skill supplements the existing brief's full-text, evidence, diversity and reading-time requirements.

Do not infer authoritativeness from preference: liking detailed equations does not make an equation-based paper better. Explicit current requests override learned preferences. Document which preference IDs influenced a brief in its local run record; do not add boilerplate about personalization to every paper.

## Learn from supplied records

Read [references/learning-policy.md](references/learning-policy.md) before ingestion, extraction or reviewing a hypothesis. Read [references/record-format.md](references/record-format.md) for the import format and commands.

Preserve original turns and their authors. Extract tentative observations from the user's own requests, corrections and explicit evaluations, anchored to exact quotes and message indices. Assistant answers, quoted paper text, silence and lack of objection are not preference evidence. Do not scan unrelated chats or private folders for records.

Keep learning incremental: ingest new records, record narrow hypotheses, then stop unless there is enough new evidence for review. Do not invent traits to fill the profile. Return a short account of what was observed, what remains uncertain and whether any established preference changed.
