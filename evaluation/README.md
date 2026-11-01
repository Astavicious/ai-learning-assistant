# Evaluation method

The original sample corpus is five authored documents, ten physical PDF pages. It is distinct from the 2025 prototype's historical 25-document corpus and 300+ interactions.

`development-v1.json` is for tuning. `acceptance-v1.json` was frozen before retrieval evaluation, with 30 answerable and 10 unsupported questions. Expected pages and per-question rubrics are fixed. Do not tune retrieval rankings or expected answers on acceptance failures. Record implementation defect repairs and distinguish follow-up checks from the original run; never silently replace failed results.

Run `PYTHONPATH=backend uv run python scripts/evaluate.py` after starting the backend and waiting for sample indexing. Add `--answers --secret-file <private-key-file>` for generation. The key is read into the evaluator process, never written to results.

Retrieval passes when the expected document AND physical page appears among at most six passages for at least 27/30 questions. Similar content on another page does not count. Answer review must inspect every substantive claim, expected rubric, and cited passage; mark correct only when the answer is substantively correct and supported. Unsupported questions must explicitly decline to answer from missing evidence (target 9/10). Citation provenance alone does not establish answer correctness. Blank manual scores mean unreviewed, never passed.

Report model ID, dataset hash/version, commit, date, sample indexing duration, warm latency, process memory, token usage, and failed cases. A local process-memory measurement does not prove Render container feasibility. Model calls in a separate evaluator process do not establish end-to-end API latency. No new answer-quality result is claimed until manual review is complete.

## Staged v1 results, 1 November 2026

`results/review-v1.json` records 30/30 retrieval page hits, 27/30 supported correct answers, and 10/10 unsupported refusals. This was a Codex-assisted manual review against the frozen rubric and actual source pages, not independent human grading. It is a staged development evaluation with recorded transient retries, not an untouched single-run benchmark of the final deployed commit.

The first run hit provider rate limits and conservatively exhausted an application reservation budget. Its raw failures remain in `answers-initial-attempt-v1.json`. The resumed run deliberately spaced requests and refunded only known rejected 429 reservations. It retained completed answers and recorded remaining failures in `answers-v1.json`. A focused live citation recheck is in `citation-recheck-v1.json`; its a13 draft changed an ASCII hyphen to a nonbreaking hyphen. The tested resolver now recognizes only specified punctuation equivalents and returns the actual original source spelling. Review applies that resolver to the saved real draft; it does not invent a replacement answer.

Three answerable questions count as unsuccessful: a05 overclaims what immutability guarantees; a11 adds a cost explanation not established by the provided text; a18 delivered no validated answer and its recheck was rate limited. All reviewed displayed citations were independently checked against their physical sample pages. No failed question is excluded from the denominator.

The 0.75-second median and 36.968-second maximum describe saved successful model calls, excluding retrieval, intentional pacing, and browser job polling, but including SDK retry waits. Provider-reported usage totals 112,153 tokens across evaluation calls, including drafts rejected by citation validation. Rejected 429 calls do not consume the token reservation. `indexing-v1.json` measures five PDFs/ten pages in a cold local Windows process with model files cached: 8.375 seconds and 285.37 MiB sampled peak combined parent/child RSS at 20ms intervals. The CI container test separately verifies sample startup under a 512 MiB cap.

A fresh single-run evaluation and independent human review would provide stronger evidence. These results should not be described as general accuracy on arbitrary course PDFs or as the historical 2025 results.
