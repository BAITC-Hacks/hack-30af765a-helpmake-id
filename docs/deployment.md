# Backend CI/CD

GitHub Actions runs `make check`, `make test` (including the 90% coverage gate),
and a Docker build for pull requests and pushes to `main`. A successful `main`
run transfers that exact image over SSH and starts it on `backend-hr`. Docker
binds the API to `127.0.0.1:8010`; nginx serves it at
`https://api.helpmake-id.live`. The container is accepted only after
its healthcheck and the HTTPS `/api/v1/ready` check pass; a failed update
restores the previous container.
`workflow_dispatch` can redeploy the current `main` commit.

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
4. Optionally add `DEPLOY_ENV_FILE` with the Docker environment-file content
   needed by the backend. Use [env.example](../deploy/env.example) as a
   starting point. Without this secret, the deploy defaults to
   `CORS_ORIGINS=https://helpmake-id.live`. The backend always allows this
   frontend origin and ignores `*` in `CORS_ORIGINS`. Put `AI_API_URL`,
   `AI_API_KEY`, and `AI_MODEL` here if the advisor endpoint should use an
   external provider. Use one `KEY=value` per
   line and no shell `export` statements.

The deploy job references the GitHub `production` environment. You may add
environment protection rules in GitHub if desired. Secrets can be repository
secrets or environment secrets in `production`. No private key or application
secret is committed to this repository.

After the first successful deployment, check
`https://api.helpmake-id.live/api/v1/ready`. The server-side container is named
`akim-backend-prod`; logs are available with
`docker logs akim-backend-prod`. The reverse proxy for `api.helpmake-id.live`
must forward HTTPS traffic to the backend on port 8010.
