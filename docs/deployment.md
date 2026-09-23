# Manual deployment

There are no GitHub workflows. A push to `main` does not deploy either service.
Run these commands from a checkout of the desired commit on `backend-hr`
(`20.124.93.89`), or build the images elsewhere for Linux x86-64 and transfer
them to that server. Keep credentials and `deploy.env` on the server, outside
Git.

## Backend

Nginx forwards `api.helpmake-id.live` to `127.0.0.1:8010`. The backend runs in
`akim-backend-prod` on the private Docker network `akim-private`, alongside the
healthy PostgreSQL 17 container `akim-postgres-prod`. PostgreSQL data is stored
in the named volume `akim-postgres-data` and port 5432 is not published.

Create `~/akim-ai-backend/deploy.env` with mode `600`. See
[env.example](../deploy/env.example) for supported keys. It must include
`DATABASE_URL=postgresql+asyncpg://akim:<password>@akim-postgres-prod:5432/akim`
with the password used by PostgreSQL. Set `CORS_ORIGINS=https://helpmake-id.live`
and, if the advisor is enabled, `AI_API_URL`, `AI_MODEL`, and `AI_API_KEY`.
Optional `AI_API_KEY_1`, `AI_API_KEY_2`, and `AI_API_KEY_3` support key rotation.
Do not commit real values. Back up the PostgreSQL volume before schema changes.

From the repository checkout on the server:

```bash
sha=$(git rev-parse HEAD)
install -d -m 700 "$HOME/akim-ai-backend"
install -m 700 deploy/deploy.sh "$HOME/akim-ai-backend/deploy.sh"
docker build -t "akim-backend:$sha" backend
docker save "akim-backend:$sha" | gzip > "$HOME/akim-ai-backend/backend-image.tar.gz"
bash "$HOME/akim-ai-backend/deploy.sh" "$sha"
```

`deploy.sh` applies Alembic migrations before switching the API container. It
checks the container health and HTTPS `/api/v1/ready` endpoint, and restores the
previous container if the switch fails. The old `akim-scenarios` SQLite volume
is retained but is not used by the PostgreSQL backend.

## Frontend

Nginx forwards `helpmake-id.live` to `127.0.0.1:3001`. The static Vite build
runs in the `akim-frontend-prod` Docker container. The
[Dockerfile](../frontend/Dockerfile) builds it with
`VITE_API_BASE_URL=https://api.helpmake-id.live` by default.

From the repository checkout on the server, build and test the new image on a
temporary port before switching the live container:

```bash
sha=$(git rev-parse HEAD)
docker build -t "akim-frontend:$sha" frontend
docker run -d --name akim-frontend-candidate \
  -p 127.0.0.1:3002:80 "akim-frontend:$sha"
docker inspect --format '{{.State.Health.Status}}' akim-frontend-candidate
curl --fail http://127.0.0.1:3002/
docker rm -f akim-frontend-candidate

docker stop akim-frontend-prod
docker rename akim-frontend-prod akim-frontend-previous
docker run -d --name akim-frontend-prod --restart unless-stopped \
  -p 127.0.0.1:3001:80 "akim-frontend:$sha"
curl --fail https://helpmake-id.live/
```

After the new container is healthy and the public site works, remove
`akim-frontend-previous`. If validation fails, remove the new container, rename
`akim-frontend-previous` back to `akim-frontend-prod`, and start it. Check the
API separately at `https://api.helpmake-id.live/api/v1/ready`.
