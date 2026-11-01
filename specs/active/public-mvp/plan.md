# Approved implementation plan

- [ ] Foundation: separate repository, locked tools, CI, deployment configuration; live upload/citation slice; free-memory check.
- [ ] Session and document foundation: ownership, expiry/deletion, staged extraction/indexing, limits and recoverable errors.
- [ ] Retrieval/generation: page chunks, hybrid ranks, selected-source filtering, validated evidence, bounded history.
- [ ] Study workspace: accessible desktop/mobile layout, source inspection, summary/quiz/cards, exports.
- [ ] Operational controls: quotas, cache, safe Markdown, restart recovery, privacy.
- [ ] Evaluation: original samples, frozen acceptance data, regression suite, honest measured results.
- [ ] Publication: repository docs/screenshots; verified demo; fresh portfolio checkout and case study.

Execute in order, refining tasks for correctness. Validate meaningful behavior test-first; full pytest, frontend tests/build, Playwright, live provider and deployed smoke checks before completion. Stop for product-scope changes. No paid upgrades or invented performance claims. Deployment and memory gates remain open until observed.
