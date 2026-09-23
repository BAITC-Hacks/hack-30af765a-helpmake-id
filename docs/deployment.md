# Backend CI/CD

GitHub Actions runs `make check`, `make test` (including the 90% coverage gate),
and a Docker build for pull requests and pushes to `main`. A successful `main`
run transfers that exact image over SSH and starts it on `backend-hr`. Docker
binds the API to `127.0.0.1:8010`; nginx serves it at
`https://api.helpmake-id.live`. The container is accepted only after
its healthcheck and the HTTPS `/api/v1/ready` check pass; a failed update
restores the previous container.
`workflow_dispatch` can redeploy the current `main` commit.
Saved scenarios live in the named Docker volume `akim-scenarios`, mounted at
`/var/lib/akim`. The container runs one Uvicorn worker for this SQLite-backed
MVP. The first `/ready` call creates schema version 1; later versions are
rejected until an explicit migration is implemented. Replacing the container
does not remove the volume. Back up the volume before changing the storage
schema, and do not remove it when cleaning old images.

## One-time setup

1. On `20.124.93.89`, install Docker Engine, ensure `useradmin` can run
   `docker` without `sudo`, and configure nginx to proxy
   `api.helpmake-id.live` to `127.0.0.1:8010`. The image is built for Linux
   x86-64. The workflow
   creates `~/akim-ai-backend` itself.
2. In the repository's GitHub **Settings → Secrets and variables → Actions**,
   add `DEPLOY_SSH_KEY` with the full private key for `useradmin`. The
   `IdentityFile` path in the local SSH config is a path on your computer; it
   cannot be used by GitHub's runner.
3. Add `DEPLOY_KNOWN_HOSTS` with the server's verified SSH host-key line for
   `20.124.93.89`. From a trusted machine, inspect its fingerprint before
   storing it; `ssh-keyscan -H 20.124.93.89` can produce the line, but does
   not authenticate the server by itself.
4. For the AI advisor, add GitHub Actions **secret** `AI_API_KEY` with an
   OpenAI Platform API key, without quotes or `Bearer `. Promotional credit
   codes belong in OpenAI Billing and are not API keys. One API key can use
   credits applied to its account. Add GitHub Actions **variables**
   `AI_API_URL=https://api.openai.com/v1/chat/completions` and
   `AI_MODEL=gpt-4.1-mini`. The deploy job passes these settings to the
   backend. Optional `AI_API_KEY_1`, `AI_API_KEY_2`, and `AI_API_KEY_3`
   secrets support multiple API keys; when any is set, the advisor tries
   numbered keys in order on 401, 402, 403, or 429 responses. Configure
   spending limits with OpenAI; GitHub secrets only store credentials.
5. Optionally add `DEPLOY_ENV_FILE` with other Docker environment-file content
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

To test the OpenAI key after setting the secret and variables, run **Verify OpenAI
API keys** from the repository's Actions tab. It sends one short chat request
per configured key and reports whether each request succeeded without printing keys.
This checks chat access for `AI_MODEL`; it does not report remaining credits.

After the first successful deployment, check
`https://api.helpmake-id.live/api/v1/ready`. The server-side container is named
`akim-backend-prod`; logs are available with
`docker logs akim-backend-prod`. The reverse proxy for `api.helpmake-id.live`
must forward HTTPS traffic to the backend on port 8010.
