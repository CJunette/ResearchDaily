# Editorial policy

## Full-text evidence

A paper is eligible only after directly inspecting the complete paper. At minimum, inspect the problem framing, related-work positioning, method, datasets or study design, main results, ablations or qualitative evidence, discussion, limitations, and any appendix needed to evaluate a central claim.

Legitimate access order:

1. Publisher or official conference open-access page.
2. Author-hosted manuscript, institutional repository, arXiv, PubMed Central, or another lawful open version.
3. User-authorized institutional or publisher account in the browser.

If access still fails, exclude the paper for the day. Ask the user for login/authorization only when needed; never request credentials in chat and never circumvent a paywall. Do not download the PDF unless the user asks.

## Quality gate

Score quality from 0 to 10. A paper below the configured threshold is ineligible even when topically relevant. Judge:

- Whether the research question matters and is clearly scoped.
- Whether the method answers that question.
- Whether comparisons, baselines, ablations, sample size, statistics, and real-world evaluation are credible for the claim.
- Whether novelty is substantive rather than a renamed component or a small benchmark gain.
- Whether limitations and generalizability are handled honestly.

Venue reputation is a prior, not proof of quality. A preprint may qualify only when unusually strong and clearly labeled as not peer reviewed. Random exploration uses the same gate.

## Plain-language standard

The first sentence must be understandable to an educated reader outside the subfield. Prefer a concrete before/after contrast:

> 以前需要把传感器贴在身上；这项工作用房间里的普通 Wi-Fi 信号完成同一件事，但目前只在少量房间里验证过。

Avoid empty phrases such as “提出了新颖框架”“取得显著提升”“具有重要意义”. Explain what the system actually does, what assumption changed, and where it may fail.

## Delta and evidence

Write the delta as: prior approach → limitation → exact change → measured benefit → cost or remaining gap. Verify the prior-work claim against the paper's related work and at least one primary neighboring work when the claim is central.

Distinguish:

- What the authors claim.
- What the experiment directly demonstrates.
- What is a plausible but untested implication.

Never turn an association into causation or a laboratory result into a deployment claim.

