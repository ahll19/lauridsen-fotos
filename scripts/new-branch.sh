#!/usr/bin/env bash
#
# Creates a correctly named branch off an up-to-date main.
#
#   scripts/new-branch.sh feat client-gallery-expiry
#
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

TYPES="feat fix docs style refactor perf test build ci chore"

usage() {
    echo "usage: scripts/new-branch.sh <type> <slug>" >&2
    echo "  type: $TYPES" >&2
    echo "  slug: lowercase words separated by hyphens, e.g. client-gallery-expiry" >&2
    exit 1
}

[[ $# -eq 2 ]] || usage

type="$1"
slug="$2"

grep -qw "$type" <<<"$TYPES" || { echo "✗ Unknown type '$type'." >&2; usage; }

if [[ ! "$slug" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
    echo "✗ Slug must be lowercase words separated by single hyphens: '$slug'" >&2
    exit 1
fi

branch="$type/$slug"

if [[ -n "$(git status --porcelain)" ]]; then
    echo "✗ Working tree is not clean. Commit or stash first." >&2
    git status --short >&2
    exit 1
fi

echo "==> Updating main"
git fetch origin main
git checkout main
git merge --ff-only origin/main

echo "==> Creating $branch"
git checkout -b "$branch"

echo "✓ On $branch, based on $(git rev-parse --short main)"
