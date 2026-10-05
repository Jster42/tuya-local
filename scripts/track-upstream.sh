#!/bin/bash
# Bring the fork up to make-all/tuya-local and keep the barn flood device file.
set -euo pipefail
cd "$(dirname "$0")/.."

git fetch origin main
git checkout main
git merge --ff-only origin/main
git push fork main

git checkout local
git merge --no-edit origin/main
git push fork local
