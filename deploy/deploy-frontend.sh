#!/usr/bin/env bash
set -euo pipefail

archive=${1:?Usage: deploy-frontend.sh <frontend-dist.tar.gz>}
revision=${2:?Usage: deploy-frontend.sh <frontend-dist.tar.gz> <revision>}

release=$(mktemp -d)
live_index=$(mktemp)
trap 'rm -rf "$release"; rm -f "$live_index"' EXIT
tar -xzf "$archive" -C "$release"
test -s "$release/index.html"
test -d "$release/assets"

# Match the file actually served by nginx. This avoids guessing its document root.
curl --fail --silent --show-error --resolve helpmake-id.live:443:127.0.0.1 \
  https://helpmake-id.live/ > "$live_index"
roots=()
while IFS= read -r -d '' candidate; do
  if cmp -s "$candidate" "$live_index"; then
    roots+=("${candidate%/index.html}")
  fi
done < <(find -L /var/www /srv/www "$HOME" -maxdepth 7 -type f -name index.html -print0 2>/dev/null || true)

if [ "${#roots[@]}" -ne 1 ]; then
  echo "Expected one nginx document root matching the live Akim AI index; found ${#roots[@]}." >&2
  exit 1
fi

root=${roots[0]}
if [ -w "$root" ]; then
  as_root=()
else
  sudo -n true
  as_root=(sudo -n)
fi

# Hashed assets go first, then index.html is replaced as the final switch.
"${as_root[@]}" install -d -m 755 "$root/assets"
"${as_root[@]}" cp -R "$release/assets/." "$root/assets/"
"${as_root[@]}" install -m 644 "$release/index.html" "$root/.index.${revision}.tmp"
"${as_root[@]}" mv -f "$root/.index.${revision}.tmp" "$root/index.html"

served=$(mktemp)
trap 'rm -rf "$release"; rm -f "$live_index" "$served"' EXIT
curl --fail --silent --show-error --resolve helpmake-id.live:443:127.0.0.1 \
  https://helpmake-id.live/ > "$served"
cmp "$release/index.html" "$served"
echo "Frontend revision $revision is live at https://helpmake-id.live/"
