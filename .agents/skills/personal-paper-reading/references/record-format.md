# Record formats and commands

Use UTF-8 JSON. The model reads and interprets records; the helper validates provenance and independence and stores decisions. It does not infer preferences from keyword counts.

Conversation format (replace illustrative values with the supplied record):

```json
{
  "id": "reading-001",
  "paper_id": "doi:10.xxxx/canonical-paper",
  "topic": "interaction-techniques",
  "read_date": "2026-11-11",
  "messages": [
    {"role": "user", "text": "先说清楚这一步解决了什么问题，再给公式。"},
    {"role": "assistant", "text": "..."}
  ]
}
```

Hypothesis format:

```json
{
  "id": "motivation-before-equations",
  "preference": "解释新方法时先说明每步解决的问题，再展开数学细节。",
  "scope": "方法解释；不改变论文质量判断或全局选题",
  "alternative_explanations": "可能只是在不熟悉的领域需要更多动机解释。",
  "evidence": [
    {"record_id": "reading-001", "message_index": 0, "quote": "先说清楚这一步解决了什么问题，再给公式。", "relation": "support", "rationale": "用户直接要求解释顺序，但目前只有单篇证据。"}
  ]
}
```

Indices are zero-based. Relations are `support`, `holdout`, or `contradict`. For each new evidence item, use the original user turn, not the assistant's paraphrase. Add evidence by importing the same unchanged hypothesis definition with additional evidence; existing evidence is deduplicated. IDs and definitions cannot be silently overwritten. After semantic review, eligible hypotheses may be activated with a rationale. Status checks show numeric readiness only, not semantic proof.

```bash
python3 scripts/reading_preferences.py ingest /path/to/record.json
python3 scripts/reading_preferences.py observe /path/to/hypothesis.json
python3 scripts/reading_preferences.py inspect
python3 scripts/reading_preferences.py inspect --id motivation-before-equations
python3 scripts/reading_preferences.py decide motivation-before-equations active --reason 'Contextual review and later-paper check support this limited scope.'
python3 scripts/reading_preferences.py decide motivation-before-equations suspended --reason 'New records suggest this applies only to unfamiliar topics.'
python3 scripts/reading_preferences.py profile
```

The default private database is `data/reading-preferences.sqlite`. `--db` can select an isolated database for tests. Inspect returns full original records when an ID is selected, to support contextual review. No eligible preferences produces an empty profile. Raw exports and analysis JSON saved in the project should go in ignored `data/reading-records/`.
