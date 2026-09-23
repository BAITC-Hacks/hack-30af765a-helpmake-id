# Backend CI/CD

The separate [frontend workflow](../.github/workflows/frontend.yml) builds the
Vite app with `VITE_API_BASE_URL=https://api.helpmake-id.live` and publishes it
to `https://helpmake-id.live` on a frontend change to `main`. It uses the same
`DEPLOY_SSH_KEY` and `DEPLOY_KNOWN_HOSTS` secrets in the `production`
environment. Its server script locates the document root by matching the
current live `index.html`, uploads hashed assets first, then replaces the
index. The deploy user needs write access to that directory or passwordless
`sudo` for the copy; an ambiguous or missing document root fails safely.

GitHub Actions runs `make check`, `make test` (including the 90% coverage gate),
and a Docker build for pull requests and pushes to `main`. A successful `main`
run transfers that exact image over SSH and starts it on `backend-hr`. Docker
binds the API to `127.0.0.1:8010`; nginx serves it at
`https://api.helpmake-id.live`. The container is accepted only after
its healthcheck and the HTTPS `/api/v1/ready` check pass; a failed update
restores the previous container.
`workflow_dispatch` can redeploy the current `main` commit.
Saved scenarios live in PostgreSQL 17 on the private Docker network
`akim-private`, in the named volume `akim-postgres-data`. The backend uses
`DATABASE_URL=postgresql+asyncpg://...` from `deploy.env`. The deployment
script runs `alembic upgrade head` in a one-off image container before it
switches the API container. `/ready` checks PostgreSQL and the expected
Alembic revision; it does not create tables. Back up the PostgreSQL volume
before a schema change. The old `akim-scenarios` SQLite volume is left intact
but is not used by the PostgreSQL backend.

## One-time setup

1. On `20.124.93.89`, install Docker Engine, ensure `useradmin` can run
   `docker` without `sudo`, and configure nginx to proxy
   `api.helpmake-id.live` to `127.0.0.1:8010`. The image is built for Linux
   x86-64. The workflow
   creates `~/akim-ai-backend` itself.
   Create a private Docker network, a persistent PostgreSQL volume, and a
   `postgres:17-alpine` container named `akim-postgres-prod` on that network.
   Keep its `postgres.env` file mode `600` and do not publish port 5432.
   Use a unique URL-safe password and put the matching URL in the protected
   `~/akim-ai-backend/deploy.env`:

   ```text
   DATABASE_URL=postgresql+asyncpg://akim:<password>@akim-postgres-prod:5432/akim
   ```

   The PostgreSQL container must be healthy before running `deploy.sh`.
2. In the repository's GitHub **Settings → Secrets and variables → Actions**,
   add `DEPLOY_SSH_KEY` with the full private key for `useradmin`. The
   `IdentityFile` path in the local SSH config is a path on your computer; it
   cannot be used by GitHub's runner.
3. Add `DEPLOY_KNOWN_HOSTS` with the server's verified SSH host-key line for
   `20.124.93.89`. From a trusted machine, inspect its fingerprint before
   storing it; `ssh-keyscan -H 20.124.93.89` can produce the line, but does
   not authenticate the server by itself.
4. For the AI advisor, add GitHub Actions **secret** `AI_API_KEY` with a
   provider API key, without quotes or `Bearer `. Add GitHub Actions
   **variables** `AI_API_URL` (the complete chat-completions URL) and
   `AI_MODEL` (the model or Azure deployment name). For OpenAI Platform,
   use `AI_API_URL=https://api.openai.com/v1/chat/completions` and a model
   available to the key. For the HR Azure OpenAI resource, use its endpoint
   followed by `/openai/v1/chat/completions` and its deployment name. Azure
   usage is billed through Azure and does not draw on OpenAI Platform
   promotional credits. The deploy job passes these settings to the backend.
   Optional `AI_API_KEY_1`, `AI_API_KEY_2`, and `AI_API_KEY_3` secrets support
   multiple API keys; when any is set, the advisor tries numbered keys in
   order on 401, 402, 403, or 429 responses. Promotional credit codes are
   not API keys.
5. Add GitHub Actions secret `DATABASE_URL` with the same PostgreSQL URL,
   or include it in `DEPLOY_ENV_FILE`. It is required for deployment. The
   GitHub runner does not need direct database access; the deployment script
   runs Alembic inside the private Docker network.
6. Optionally add `DEPLOY_ENV_FILE` with other Docker environment-file content
   needed by the backend. Use [env.example](../deploy/env.example) as a
   starting point. Without this secret, the deploy defaults to
   `CORS_ORIGINS=https://helpmake-id.live`. The backend always allows this
   frontend origin and ignores `*` in `CORS_ORIGINS`. The AI settings above
   can also be set here. Use one `KEY=value` per line and no shell `export`
   statements. Nonempty individual GitHub variables and secrets override
   matching entries in `DEPLOY_ENV_FILE`.

The deploy job references the GitHub `production` environment. You may add
environment protection rules in GitHub if desired. Secrets can be repository
secrets or environment secrets in `production`. No private key or application
secret is committed to this repository.

To test the provider key after setting the secret and variables, run **Verify AI
provider key** from the repository's Actions tab. It sends one short chat request
per configured key and reports whether each request succeeded without printing keys.
This checks chat access for `AI_MODEL`; it does not report remaining credits.

After the first successful deployment, check
`https://api.helpmake-id.live/api/v1/ready`. The server-side container is named
`akim-backend-prod`; logs are available with
`docker logs akim-backend-prod`. The reverse proxy for `api.helpmake-id.live`
must forward HTTPS traffic to the backend on port 8010.
