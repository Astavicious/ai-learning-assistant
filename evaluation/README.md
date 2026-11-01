# Evaluation method

The original sample corpus is five authored documents, ten physical PDF pages. It is distinct from the 2025 prototype's historical 25-document corpus and 300+ interactions.

`development-v1.json` is for tuning. `acceptance-v1.json` was frozen before retrieval evaluation, with 30 answerable and 10 unsupported questions. Expected pages and per-question rubrics are fixed. Do not tune on acceptance failures; record failures and use a new version for future changes.

Run `PYTHONPATH=backend uv run python scripts/evaluate.py` after starting the backend and waiting for sample indexing. Add `--answers --secret-file <private-key-file>` for generation. The key is read into the evaluator process, never written to results.

Retrieval passes when the expected document AND physical page appears among at most six passages for at least 27/30 questions. Similar content on another page does not count. Answer review must inspect every substantive claim, expected rubric, and cited passage; mark correct only when the answer is substantively correct and supported. Unsupported questions must explicitly decline to answer from missing evidence (target 9/10). Citation provenance alone does not establish answer correctness. Blank manual scores mean unreviewed, never passed.

Report model ID, dataset hash/version, commit, date, sample indexing duration, warm latency, process memory, token usage, and failed cases. A local process-memory measurement does not prove Render container feasibility. Model calls in a separate evaluator process do not establish end-to-end API latency. No new answer-quality result is claimed until manual review is complete.
