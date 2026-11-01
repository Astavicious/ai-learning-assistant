# Free deployment runbook

Deployment configuration is present; a live URL is not a verified demo until the smoke checks pass.

## Render backend

Use the root Dockerfile and `render.yaml`, selecting **Free**, one web worker, no persistent disk. The image bakes the embedding model into `/app/model-cache`; session files are written only to `/tmp/study`. Set `GROQ_API_KEY`, exact frontend `ALLOWED_ORIGINS`, configurable `GENERATION_MODEL`, and a conservative `GLOBAL_DAILY_TOKENS` within the account allowance. Do not print environment variables or enable access logs containing private query parameters. The API uses header-based authorization, never query-string tokens.

Test the container under the actual free memory limit. A local Python process measurement does not establish the container's limit. Inspect startup, model load, sample indexing, a maximum-size allowed upload, and generation. Keep paid upgrades disabled.

Free services sleep and lose their filesystem. `/api/health` reports sample readiness and key configuration without exposing secrets. The interface retries startup and explicitly handles a rejected expired-session token. Verify sample rebuilding after a restart and recovery in an existing browser session.

## Vercel frontend

Use project root `frontend`, Vite framework, Node 22, `npm ci`, `npm run build`, output `dist`. Set `VITE_API_URL` to the verified backend origin before building. Configure the backend CORS origin to the production frontend domain. Keep model/deployment credentials out of all `VITE_*` variables and client bundles.

Vercel hosts the static frontend. The current backend depends on a single running process, temporary SQLite/session data, and 10 MB uploads. Moving it to Vercel Functions would require direct object-storage uploads and shared external storage/jobs because function request limits and isolated temporary files do not match this design.

## Release checks

1. Fresh browser loads the frontend with no preexisting session.
2. Sleeping backend wakes and samples become ready.
3. Live chat returns validated citations that open a real page.
4. Private upload, quiz, summary, cards, and exports succeed.
5. Another session cannot access private sources or jobs.
6. Session deletion removes private resources; restart recovery is explicit.
7. All 40 acceptance questions have recorded, reviewed results meeting the agreed gates.
8. Add the verified URL to GitHub About and the portfolio case study; verify the deployed links.
