# Source map

This is a venue/reference registry. Resolve collection strategy through `config/discovery.json` and its skill; this file does not prescribe a parallel search workflow. Use official proceedings, publisher pages, or first-party repositories for discovery and full text. Use OpenAlex, Crossref, and Semantic Scholar for normalization and citation cross-checks, not as substitutes for reading the paper.

Operational routing differs from bibliographic publication type: IMWUT, TOCHI, PACMHCI and similar specialist serials belong to the conference/specialist-catalog route. Reserve the journal route for Nature/Science flagships and research journals, and comparable journals such as Cell, PNAS and The Lancet. Preserve each item's actual venue/type. These routes do not determine the four brief sections.

## Core HCI, UbiComp, and sensing

- HCI: CHI, UIST, CSCW/PACMHCI, DIS, IUI, MobileHCI, ASSETS, TEI.
- UbiComp/mobile/sensing: IMWUT/UbiComp, MobiSys, MobiCom, SenSys, IPSN, PerCom, ISWC.
- Specialist catalogs (conference route): TOCHI, PACMHCI, IEEE Pervasive Computing, and relevant ACM/IEEE transactions.
- Search themes: wearable/mobile/ambient/contactless sensing; RF, radar, acoustic, physiological, and multimodal sensing; activity and context recognition; personal informatics; privacy; accessibility; real-world deployment; on-device learning.

## Adjacent fields

- Health: CHIL, ML4H, AMIA/JAMIA, npj Digital Medicine, Nature Medicine, The Lancet Digital Health, JMIR, PubMed, medRxiv, bioRxiv.
- AI and vision: ICLR, NeurIPS, ICML, AAAI, CVPR, ICCV, ECCV, ACL, EMNLP, OpenReview, CVF Open Access.
- Robotics: HRI, RSS, CoRL, ICRA, IROS.

## Heavyweight and serendipity

The explicit journal list with URLs and subject-rotation hints is `config/sources.json.journal_catalogs`; use it rather than maintaining a separate exhaustive list here. It now covers computing/AI, electronics/sensing, biomedical/clinical, behavior and review journals. Registry membership is not a claim that every article is heavyweight.

- Nature, Science, PNAS, Cell, Nature Human Behaviour, Nature Machine Intelligence, Communications of the ACM.
- High-quality Reviews, Perspectives, and Commentaries may qualify when they contain a genuinely useful conceptual shift.
- Serendipity may come from any field, but must offer a concrete method, result, research instrument, or conceptual frame that could expand scientific perspective. Popularity alone is insufficient.

## AI 新动向 (fifth section)

Use arXiv category updates plus optional recommendation leads for early AI ideas/applications. Categories and endpoints are in `config/sources.json.ai_frontier`; collection/quality/status rules are in the discovery skill's `references/ai-frontier.md`. arXivLabs integrations are third-party tools, not peer review or arXiv quality endorsements. Output 0–1 full-text-verified items within the existing daily time ceiling.

## Identity and metrics

- Prefer DOI as the canonical identity; otherwise use arXiv/OpenReview identifiers and normalized title matching.
- Merge preprints with later proceedings or journal versions.
- State whether the item is peer reviewed.
- Label citation counts by provider and retrieval date. Do not combine counts from different providers or describe a count as readership.
- Publisher view/download counts may be used only when publicly visible and should be labeled separately from citations.

