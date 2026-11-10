# Full-text review schema

Create a UTF-8 JSON object or JSON array and pass it to:

```bash
python3 scripts/research_daily.py record-review /path/to/review.json
```

Required object:

```json
{
  "paper_id": "p_identifier_from_list_candidates",
  "full_text_read": true,
  "full_text_url": "https://legitimate-full-text-location.example/paper",
  "access_method": "open_access | author_copy | institutional | publisher_account",
  "read_at": "2026-11-10T08:00:00+00:00",
  "plain_language_takeaway": "用没有行话的一两句话说清楚本文到底改变了什么、为什么值得关心。",
  "problem": "具体研究问题，以及这个问题为什么尚未解决。",
  "method": "用自己的话概括系统、数据、研究设计与比较对象。",
  "contributions": [
    "可验证的贡献一",
    "可验证的贡献二"
  ],
  "delta": "过去做法 → 限制 → 本文的准确改变 → 结果 → 代价或仍未解决的部分。",
  "evidence": "哪些实验支持哪些结论；哪里证据不足。",
  "limitations": "作者承认的和阅读全文后识别出的主要局限。",
  "why_read": "与当前兴趣或科研视野的具体联系。",
  "sections_to_read": "建议优先看的图、表和章节。",
  "reading_minutes": 6,
  "quality_score": 8.0,
  "relevance_score": 9.0,
  "innovation_score": 8.0,
  "reviewer_notes": "可选的内部核验备注"
}
```

`full_text_read` 必须是真正的 JSON boolean `true`。若只读到摘要，不要创建审阅记录。分数范围为 0–10；阅读时间范围为 2–20 分钟。
