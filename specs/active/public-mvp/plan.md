# Approved implementation plan

- [x] Foundation: separate repository, locked tools, CI, deployment configuration; live upload/citation slice; free-memory check.
- [x] Session and document foundation: ownership, expiry/deletion, staged extraction/indexing, limits and recoverable errors.
- [x] Retrieval/generation: page chunks, hybrid ranks, selected-source filtering, validated evidence, bounded history.
- [x] Study workspace: accessible desktop/mobile layout, source inspection, summary/quiz/cards, exports.
- [x] Operational controls: quotas, cache, safe Markdown, restart recovery, privacy.
- [x] Evaluation: original samples, frozen acceptance data, regression suite, honest measured results.
- [x] Publication: repository docs/screenshots; verified demo; fresh portfolio checkout and case study.

Executed in order, refining tasks for correctness. Validated meaningful behavior test-first, full pytest, frontend tests/build, desktop/mobile Playwright, live Groq requests, and deployed checks. Free Render and Vercel deployments are published. GitHub Actions verifies sample startup and UI interactions with a 512 MiB container cap. No paid upgrades were selected.

Evaluation is a documented staged, assisted rubric review with preserved failures and retries, not independent human grading or an untouched single-run final-commit benchmark. Natural 15-minute idle sleep was not separately timed; initial/redeployment startup, sample rebuilding, interrupted jobs, session expiry, and restart recovery were checked. See docs/release-validation.md for evidence and practical limits. Retention/archive work has not been started.
