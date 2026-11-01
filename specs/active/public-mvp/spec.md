# AI Learning Assistant public MVP

## Summary
Expand the original 2025 local prototype into a separate, public, anonymous PDF study application, GitHub repository, and portfolio case study. The approved conversation dated 2026-11-01 is the source specification.

## Scope and decisions
React/TypeScript/Vite; FastAPI/Pydantic; pypdf/PDF.js; FastEmbed BAAI/bge-small-en-v1.5; SQLite FTS5/NumPy; configurable Groq openai/gpt-oss-20b; Vercel/Render free hosting. Original publishable FP course: three lectures and two worksheets. Cited chat, bounded follow-ups, full-scope summaries, five-question quizzes, ten flashcards, Markdown/TSV exports, responsive accessible workspace.

## Constraints
No accounts or permanent storage. Five PDFs, 10 MB/file, 25 MB/150 pages/session; local 25-document override. Bound parsing, text/chunks, work queues, disk, and provider use. Two-hour inactivity and 24-hour absolute expiry. Ownership on all resources, citations and jobs. Immutable samples separate from uploads. Never log private content. No paid upgrades. Provider retention notice. Physical PDF pages. Validate citations and structured generation before display.

## Out of scope
OCR, handwriting, collaboration, accounts, permanent libraries, spaced repetition.

## Success criteria
Complete study workflow on desktop/mobile and keyboard. Authorized real passages for every displayed citation. Session isolation and deterministic quiz scoring tests pass. Frozen 40-question acceptance set: retrieval >=27/30, supported correct answers >=27/30, unsupported refusal >=9/10. Publish actual latency, indexing, memory and token measurements, method/model/date/dataset version. Historical 25-document/300+ interaction claims are not new results. Verified public demo, repository, and portfolio route /projects/ai-learning-assistant with 2025 original year.

## Open dependencies
Groq key and model availability; deployment access; Render memory feasibility. No benchmark results or deployment success may be claimed before verification.
