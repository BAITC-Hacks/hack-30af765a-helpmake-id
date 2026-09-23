#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! $1 =~ ^[0-9a-f]{40}$ ]]; then
  echo 'Usage: deploy.sh <40-character commit SHA>' >&2
  exit 2
fi

deployment_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
image="akim-backend:$1"
container='akim-backend-prod'
previous='akim-backend-prod-previous'
switchover_started=0
had_previous=0
committed=0
old_image=''

rollback() {
  status=$?
  trap - EXIT
  if (( status != 0 && switchover_started == 1 && committed == 0 )); then
    echo 'Deployment failed; restoring the previous container.' >&2
    if docker container inspect "$previous" > /dev/null 2>&1; then
      docker rm -f "$container" > /dev/null 2>&1 || true
      docker rename "$previous" "$container"
      docker start "$container" > /dev/null
    elif (( had_previous == 1 )); then
      docker start "$container" > /dev/null 2>&1 || true
    else
      docker rm -f "$container" > /dev/null 2>&1 || true
    fi
  fi
  exit "$status"
}
trap rollback EXIT

cd "$deployment_dir"
test -s backend-image.tar.gz
test -f deploy.env
gzip -t backend-image.tar.gz
gzip -dc backend-image.tar.gz | docker load
docker image inspect "$image" > /dev/null

if docker container inspect "$previous" > /dev/null 2>&1; then
  echo "Resolve the existing $previous container before deploying." >&2
  exit 1
fi

if docker container inspect "$container" > /dev/null 2>&1; then
  had_previous=1
  old_image="$(docker inspect --format '{{.Config.Image}}' "$container")"
fi
switchover_started=1
if (( had_previous == 1 )); then
  docker stop "$container" > /dev/null
  docker rename "$container" "$previous"
fi

docker run -d \
  --name "$container" \
  --restart unless-stopped \
  --env-file "$deployment_dir/deploy.env" \
  --publish 127.0.0.1:8010:8000 \
  --health-cmd='python -c "import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8000/api/v1/ready\", timeout=5)"' \
  --health-interval=10s \
  --health-timeout=5s \
  --health-retries=5 \
  --health-start-period=10s \
  "$image" > /dev/null

for (( attempt = 0; attempt < 60; attempt++ )); do
  health="$(docker inspect --format '{{.State.Health.Status}}' "$container")"
  if [[ $health == healthy ]]; then
    curl --fail --silent --show-error --max-time 10 \
      --resolve api.helpmake-id.live:443:127.0.0.1 \
      https://api.helpmake-id.live/api/v1/ready > /dev/null
    committed=1
    if (( had_previous == 1 )); then
      docker rm "$previous" > /dev/null || true
      if [[ $old_image != "$image" ]]; then
        docker image rm "$old_image" > /dev/null 2>&1 || true
      fi
    fi
    rm -f backend-image.tar.gz
    echo "Deployed $image and passed /api/v1/ready."
    exit 0
  fi
  if [[ $health == unhealthy ]]; then
    break
  fi
  sleep 2
done

docker logs --tail 100 "$container" >&2 || true
echo 'New container did not become healthy.' >&2
exit 1
