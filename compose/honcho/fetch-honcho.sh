#!/bin/sh
# Fetch Honcho at the pinned commit and build the UNMODIFIED upstream image from its own Dockerfile. The source is git-ignored: this repo ships none of Honcho's code.
set -eu
COMMIT=06ed1929cf017c333a87c41d130bb6a0605d91c0   # tag v3.2.2, released 2026-10-01
cd "$(dirname "$0")"
[ -d honcho-src/.git ] || git clone https://github.com/plastic-labs/honcho.git honcho-src
git -C honcho-src fetch --tags --quiet
git -C honcho-src checkout --quiet "$COMMIT"
[ "$(git -C honcho-src rev-parse HEAD)" = "$COMMIT" ] || { echo "wrong commit" >&2; exit 1; }
docker build -t honcho-pinned:v3.2.2 honcho-src
