# Conservative learning policy

## Separate the objects

- Raw records: immutable conversation turns, paper identity, topic and reading date. Keep locally; do not push them to GitHub or include them in the published website.
- Hypotheses: narrow, falsifiable preferences with scope, supporting user quotes, competing explanations and counterevidence. They do not affect output.
- Established preferences: hypotheses that passed an evidence review and later-record check. Only these personalize future briefs.

Use canonical paper identities: merge DOI/preprint/accepted versions of one paper. Repeated turns or several exports of the same paper are one independent paper, not many observations. Choose substantive topics, not venue labels; two wearable-health papers from different publishers may be one topic. Do not relabel a topic to pass a gate.

## Avoid overfitting

Questions show what needed explaining in that moment. Repeated requests for derivations may reflect an unfamiliar method. A short-answer request may reflect being busy. Interest in one application is not a global topic preference. Infer a trait only if these explanations become less plausible across independent contexts. Never copy the assistant's presentation style into the profile unless the user explicitly and repeatedly endorses it.

For an inferred preference, the default review gate is deliberately slow: support from at least four different papers, at least three substantive topics and at least three reading dates, plus support in a fifth, different paper read on a later date. Reserve that later record as a held-out check, and interpret it before looking for a way to confirm the hypothesis. These are engineering safeguards, not statistical confidence estimates; counts alone never establish a preference. Each observation needs an exact user quote and a contextual rationale. Do not manufacture the fifth observation from a continuation or re-export of an earlier conversation.

At review, inspect original contexts, credible alternative explanations, the proposed scope and possible counterexamples. Require a written review rationale. Use a narrow scope when warranted. Unresolved counterevidence blocks activation; contradictory new evidence automatically suspends an active preference until reviewed. Withdrawn/rejected hypotheses remain in the ledger for traceability. Do not silently broaden wording: create a separate hypothesis instead.

If the user explicitly states a durable preference, follow that instruction in the current task; record it as an explicit user instruction rather than claiming it was learned from several conversations. Do not ask the user to approve every weak hypothesis or repeatedly quiz them. Let uncertain hypotheses remain unused.

## Daily operation

Brief generation reads the established profile. It does not promote hypotheses just to improve personalization. Process new records when supplied; reassess only when enough independent evidence or a contradiction arrives. Keep the original quote, uncertainty and provenance so the user can inspect or reverse an interpretation.
