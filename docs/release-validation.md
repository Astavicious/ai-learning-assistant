# Release validation — 1 November 2026

## Published destinations

- Frontend: https://ai-learning-assistant-one-sigma.vercel.app
- Backend health: https://ai-learning-assistant-api-1aeb.onrender.com/api/health
- GitHub: https://github.com/Astavicious/ai-learning-assistant
- Stable CV destination: https://bilal-amin-portfolio-eight.vercel.app/projects/ai-learning-assistant

The portfolio was changed in a fresh main-branch checkout, built with zero Astro errors/warnings, inspected at desktop/mobile sizes, pushed as commit `6948ecd`, and verified on its public production domain. The homepage links to the case study. Original project year remains 2025; the expanded release and its results are labelled separately.

## Automated evidence

- 28 backend pytest checks: ownership, source/preview/job access, duplicate/corrupt/encrypted/image-only/oversized/partial PDFs, page attribution, document selection, citation rejection and punctuation resolution, token budget behavior, bounded provider retries, fixed quiz serialization, session deletion/expiry/absolute lifetime, passive polling, interrupted jobs, saved materials, and early/chunked request-size rejection.
- Three Vitest checks cover deterministic scoring, invalid answer keys, and quoted Unicode/tab/newline TSV exports.
- Four Playwright checks pass on the deployed frontend at desktop and mobile sizes. They exercise tab state, keyboard access, drawer focus, scoring/review, real PDF evidence viewing, and export. The quiz/card generation API is explicitly stubbed in these regression checks; they do not establish live model quality.
- GitHub Actions runs backend checks, generated-schema/type drift checks, frontend tests/build, and actual Docker sample startup under a 512 MiB cap. Browser tests also run against that constrained container. No local Docker installation was available.

## Live checks

Real requests to the public backend verified private upload and indexing, physical page text, authorized PDF preview, duplicate rejection, cross-session denial of reading/deletion, and deletion. Live Groq calls produced a validated cited answer, five-question quiz, ten flashcards, and a full two-page summary. A fresh-browser live quiz (without API fixtures) rendered five questions with four options, calculated the score checked independently against the returned answer key, revealed explanations/citations, and downloaded Markdown. Screenshots of an actual live cited answer/PDF and live quiz review are in `docs/screenshots`.

Initial live checks deliberately exposed failures that remain documented: model typography changed a source hyphen; nested array decoding inserted empty entries between quiz questions; provider rate limits interrupted calls. The resolver now maps only specific punctuation equivalents back to the real source spelling. Internal fixed quiz/option slots avoid the observed array decoding defect, and application validation still rejects malformed or unsupported results. Known structured-generation errors have one bounded retry. Failed results are not displayed as successful answers.

## Evaluation and limits

The frozen 40-question dataset, original results, retries, focused recheck and assisted manual judgments are published under `evaluation`. Staged results are 30/30 retrieval hits, 27/30 supported correct answers, and 10/10 unsupported refusals. This is not independent human review or an untouched final-commit single run. Three unsuccessful answers remain in the denominator. Local sample indexing, memory, token usage and model-call latency measurements have explicit workload/method boundaries.

Free-service restart loses temporary files and sessions; sample availability rebuilt successfully after deployment. Expiry, interrupted work, and rejected-session recovery are covered by checks. Natural 15-minute idle sleep was not separately timed, and maximum-load/adversarial resource exhaustion was not benchmarked. A local process-memory measurement and a 512 MiB startup test do not guarantee every permitted PDF fits the host. Per-file/session/text/chunk/queue/body/parser limits constrain this risk; oversized or unsupported files fail explicitly.

No paid plan or automatic upgrade was enabled. Independent human answer review, a fresh single-run benchmark, and wider document/device testing remain useful follow-ups, rather than claims made by this release.
