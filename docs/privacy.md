# Privacy, sessions, and limits

The browser stores a random session access token in session storage. Treat it as a credential; no account is required. The backend stores only its SHA-256 hash. Every private document, preview, passage, job, and material request checks session ownership. Samples are public immutable resources, accessible through an active session.

Uploaded PDF bytes, extracted page text, chunks, embeddings, jobs, validated outputs, and generation caches are held in temporary backend storage. Sessions expire after two hours without an interactive API action and no later than 24 hours after creation. Passive status/document polling does not extend inactivity. Closing a browser does not immediately delete server-side data; use Delete session for immediate application deletion. Cleanup runs periodically and at startup. Render free-service sleep, restart, and redeploy can remove all temporary state sooner.

Relevant extracted passages, the current generation task, and a bounded recent conversation are sent to Groq. Full selected text is sent in bounded batches when requesting a summary. The original PDF file is not sent to Groq. Deleting application data cannot promise deletion of provider-retained copies. Review [Groq's data controls and retention policy](https://console.groq.com/docs/your-data).

Limits: 5 PDFs/session (25 with a local count override), 10 MB/file, 25 MB/150 pages/session, 1 million extracted characters/session, 2,000 chunks/session, 30-second parsing timeout, 8 globally active/queued jobs and 2 per session. Indexing and generation are serialized independently. Uploaded PDF storage is bounded globally. Daily generation is pre-reserved and reconciled with provider-reported usage; unknown failed-request usage retains the reservation. Request rates are limited per source IP. Exact account/provider limits can be lower than application limits.

Usage counters do not store questions or document text. Generated materials and caches may contain private text and are session-owned. Removing a private document invalidates all derived jobs/materials/caches in that session to avoid stale citations. Provider-side usage limits remain authoritative after host restarts.

PDF extraction limitations include complex columns, mathematical notation, unusual font encodings, code indentation, and scanned pages. Whitespace is preserved where extraction permits. Image-only and password-protected files are rejected; partially readable PDFs identify unreadable physical pages. OCR is outside scope.
