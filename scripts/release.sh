#!/usr/bin/env bash
#
# Prepares and publishes releases.
#
# Releases happen in two steps because main cannot be pushed to directly:
#
#   scripts/release.sh prepare <major|minor|patch>
#       Bumps VERSION, writes the CHANGELOG section from the commits since the last tag,
#       and opens a pull request. Review and merge it on GitHub.
#
#   scripts/release.sh tag
#       Run on main once that pull request is merged. Creates and pushes the annotated tag.
#
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

die() { echo "✗ $*" >&2; exit 1; }

require_clean_tree() {
    [[ -z "$(git status --porcelain)" ]] || die "Working tree is not clean. Commit or stash first."
}

current_version() {
    [[ -f VERSION ]] || die "VERSION file is missing."
    tr -d '[:space:]' < VERSION
}

# ---------------------------------------------------------------------------
prepare() {
    local bump="${1:-}"
    case "$bump" in
        major|minor|patch) ;;
        *) die "usage: scripts/release.sh prepare <major|minor|patch>" ;;
    esac

    require_clean_tree
    command -v gh >/dev/null || die "gh is required to open the release pull request."

    local old new major minor patch
    old=$(current_version)
    IFS='.' read -r major minor patch <<<"$old"

    case "$bump" in
        major) major=$((major + 1)); minor=0; patch=0 ;;
        minor) minor=$((minor + 1)); patch=0 ;;
        patch) patch=$((patch + 1)) ;;
    esac
    new="$major.$minor.$patch"

    echo "==> Releasing $old -> $new"

    git fetch origin main --tags
    git checkout main
    git merge --ff-only origin/main

    local branch="chore/release-v$new"
    git checkout -b "$branch"

    echo "$new" > VERSION

    local last_tag range
    last_tag=$(git describe --tags --abbrev=0 2>/dev/null || true)
    if [[ -n "$last_tag" ]]; then
        range="$last_tag..HEAD"
        echo "    Collecting commits since $last_tag"
    else
        range="HEAD"
        echo "    No previous tag; collecting all commits"
    fi

    write_changelog "$new" "$range"

    git add VERSION CHANGELOG.md
    git commit -m "chore(release): v$new" \
               -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"

    git push -u origin "$branch"
    gh pr create --base main --head "$branch" \
        --title "chore(release): v$new" \
        --body "Version bump and changelog for v$new.

Merge this, then run \`scripts/release.sh tag\` on main to publish the tag."

    echo
    echo "✓ Release PR opened for v$new. Merge it, then run: scripts/release.sh tag"
}

# Rewrites CHANGELOG.md, moving Unreleased content into a dated section for $1 and adding
# entries derived from the Conventional Commit subjects in range $2.
write_changelog() {
    local version="$1" range="$2"
    local date; date=$(date +%Y-%m-%d)
    local tmp; tmp=$(mktemp)

    {
        # Everything above the Unreleased heading, plus a fresh empty Unreleased section.
        sed '/^## \[Unreleased\]/,$d' CHANGELOG.md
        echo "## [Unreleased]"
        echo
        echo "## [$version] - $date"
        echo

        section "Added"      "feat"     "$range"
        section "Fixed"      "fix"      "$range"
        section "Changed"    "refactor|perf|style" "$range"
        section "Maintenance" "build|ci|chore|test|docs" "$range"

        # Preserve whatever was already hand-written under the old Unreleased heading.
        local carried
        carried=$(sed -n '/^## \[Unreleased\]/,/^## \[/p' CHANGELOG.md | sed '1d;$d' | sed '/^\s*$/d')
        if [[ -n "$carried" ]]; then
            echo "$carried"
            echo
        fi

        # Everything from the previous released section onwards.
        sed -n '/^## \[Unreleased\]/,$p' CHANGELOG.md | tail -n +2 | sed -n '/^## \[/,$p'
    } > "$tmp"

    mv "$tmp" CHANGELOG.md
}

# section <heading> <type-regex> <git-range>
section() {
    local heading="$1" types="$2" range="$3" entries
    entries=$(git log --no-merges --pretty=format:'%s' "$range" \
        | grep -E "^($types)(\([^)]+\))?!?: " \
        | sed -E "s/^($types)(\(([^)]+)\))?!?: /\3|/" \
        | awk -F'|' '{ if ($1 != "") printf "- **%s**: %s\n", $1, $2; else printf "- %s\n", $2 }' \
        || true)

    if [[ -n "$entries" ]]; then
        echo "### $heading"
        echo
        echo "$entries"
        echo
    fi
}

# ---------------------------------------------------------------------------
tag() {
    require_clean_tree

    local branch; branch=$(git rev-parse --abbrev-ref HEAD)
    [[ "$branch" == "main" ]] || die "Tag from main, not '$branch'. Merge the release PR first."

    git fetch origin main --tags
    [[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] \
        || die "Local main differs from origin/main. Pull first."

    local version; version=$(current_version)
    local tag="v$version"

    git rev-parse "$tag" >/dev/null 2>&1 && die "Tag $tag already exists."
    grep -q "^## \[$version\]" CHANGELOG.md || die "CHANGELOG.md has no section for $version."

    local notes
    notes=$(awk "/^## \[$version\]/{flag=1; next} /^## \[/{flag=0} flag" CHANGELOG.md)

    git tag -a "$tag" -m "Release $tag" -m "$notes"
    git push origin "$tag"

    echo "✓ Tagged and pushed $tag"
}

# ---------------------------------------------------------------------------
case "${1:-}" in
    prepare) shift; prepare "$@" ;;
    tag)     tag ;;
    *)       die "usage: scripts/release.sh <prepare <major|minor|patch> | tag>" ;;
esac
