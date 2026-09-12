#!/usr/bin/env bash
#
# The verification pipeline.
#
# Runs every check that must pass before a branch is fit to merge. Checks whose subject
# doesn't exist yet (no Python, no compose file, no tests) are skipped loudly rather than
# silently, so this script is useful from an empty repository onwards.
#
#   scripts/verify.sh          run everything
#   scripts/verify.sh --fast   hygiene, secrets and linting only (what pre-commit runs)
#
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

FAST=0
[[ "${1:-}" == "--fast" ]] && FAST=1

FAILED=0
SKIPPED=()

bold=$(tput bold 2>/dev/null || true)
red=$(tput setaf 1 2>/dev/null || true)
green=$(tput setaf 2 2>/dev/null || true)
yellow=$(tput setaf 3 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)

step()  { printf '\n%s==> %s%s\n' "$bold" "$1" "$reset"; }
ok()    { printf '    %s✓%s %s\n' "$green" "$reset" "$1"; }
fail()  { printf '    %s✗%s %s\n' "$red" "$reset" "$1"; FAILED=1; }
skip()  { printf '    %s–%s %s\n' "$yellow" "$reset" "$1"; SKIPPED+=("$1"); }

has() { command -v "$1" >/dev/null 2>&1; }

# Files git knows about, excluding deletions. Used so checks never look at ignored junk.
tracked_files() { git ls-files --cached --others --exclude-standard; }

# ---------------------------------------------------------------------------
step "Repository hygiene"

bad_env=$(tracked_files | grep -E '(^|/)\.env($|\.)' | grep -v '\.env\.example$' || true)
if [[ -n "$bad_env" ]]; then
    fail "an .env file is tracked: $(echo "$bad_env" | tr '\n' ' ')"
else
    ok "no .env files tracked"
fi

if [[ ! -f .gitignore ]]; then
    fail ".gitignore is missing"
else
    ok ".gitignore present"
fi

# Photographs and databases belong in the bind-mounted /data directory, never in git.
large=$(tracked_files | while read -r f; do
    [[ -f "$f" ]] || continue
    size=$(wc -c <"$f" | tr -d ' ')
    (( size > 5242880 )) && printf '%s (%s MB)\n' "$f" "$((size / 1048576))"
done || true)
if [[ -n "$large" ]]; then
    fail "files over 5 MB are staged or tracked:"
    printf '        %s\n' "$large"
else
    ok "no oversized files"
fi

if tracked_files | grep -qE '\.(sqlite3|db)$'; then
    fail "a database file is tracked — it belongs in /data, not in git"
else
    ok "no database files tracked"
fi

# ---------------------------------------------------------------------------
step "Secret scan"

if has gitleaks; then
    if gitleaks detect --no-banner --redact --exit-code 1 >/dev/null 2>&1; then
        ok "gitleaks found nothing"
    else
        fail "gitleaks found potential secrets — run: gitleaks detect --redact --verbose"
    fi
else
    # Fallback patterns for when gitleaks isn't installed. Deliberately narrow: these match
    # literal assigned values, not references to environment variables.
    patterns=(
        '-----BEGIN [A-Z ]*PRIVATE KEY-----'
        'AKIA[0-9A-Z]{16}'
        'gh[pousr]_[A-Za-z0-9]{36}'
        '(SECRET_KEY|PASSWORD|API_KEY|TOKEN)[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'$\{]{12,}["'"'"']'
    )
    found=0
    for p in "${patterns[@]}"; do
        # Exclude this script itself, which necessarily contains the patterns.
        hits=$(tracked_files | grep -v '^scripts/verify.sh$' | xargs -r grep -lEI "$p" 2>/dev/null || true)
        if [[ -n "$hits" ]]; then
            fail "possible secret matching /$p/ in: $(echo "$hits" | tr '\n' ' ')"
            found=1
        fi
    done
    (( found == 0 )) && ok "no obvious secrets (install gitleaks for a real scan)"
fi

# ---------------------------------------------------------------------------
step "Shell scripts"

shell_files=$(tracked_files | grep -E '^(scripts/.*\.sh|\.githooks/[a-z-]+)$' || true)
if [[ -z "$shell_files" ]]; then
    skip "no shell scripts found"
elif has shellcheck; then
    # shellcheck disable=SC2086
    if shellcheck -S warning $shell_files; then
        ok "shellcheck clean"
    else
        fail "shellcheck reported problems"
    fi
else
    syntax_ok=1
    for f in $shell_files; do
        bash -n "$f" || syntax_ok=0
    done
    (( syntax_ok == 1 )) && ok "bash syntax valid (install shellcheck for real linting)" \
                         || fail "bash syntax errors"
    for f in $shell_files; do
        [[ -x "$f" ]] || fail "$f is not executable (chmod +x)"
    done
fi

# ---------------------------------------------------------------------------
step "Python"

python_files=$(tracked_files | grep -E '\.py$' || true)

# Django lives in the image, not on the developer's machine, so the checks that need it
# run inside a container. CI installs requirements.txt directly and runs them in place.
django_runner() {
    if python -c "import django" >/dev/null 2>&1; then
        (cd src && python manage.py "$@")
    elif has docker && docker compose ps --services 2>/dev/null | grep -qx app; then
        docker compose run --rm --no-deps -T app python manage.py "$@"
    else
        return 127
    fi
}

if [[ -z "$python_files" ]]; then
    skip "no Python code yet"
else
    if has ruff; then
        ruff format --check . && ok "formatting clean" || fail "formatting issues — run: ruff format ."
        ruff check .          && ok "lint clean"       || fail "lint issues — run: ruff check --fix ."
    else
        skip "ruff not installed — formatting and linting (pip install ruff)"
    fi

    if [[ ! -f src/manage.py ]]; then
        skip "no manage.py — django checks"
    else
        django_runner check >/dev/null 2>&1
        rc=$?

        if (( rc == 127 )); then
            skip "django checks (no local Django, and the stack isn't running)"
        elif (( rc != 0 )); then
            fail "django system checks failed — run: scripts/dev.sh manage check"
        else
            ok "django system checks pass"

            if django_runner makemigrations --check --dry-run >/dev/null 2>&1; then
                ok "no missing migrations"
            else
                fail "models changed without a migration — run: scripts/dev.sh manage makemigrations"
            fi

            if (( FAST )); then
                skip "test suite (--fast)"
            elif django_runner test --verbosity 1 >/dev/null 2>&1; then
                ok "tests pass"
            else
                fail "tests failed — run: scripts/dev.sh manage test"
            fi
        fi
    fi
fi

# ---------------------------------------------------------------------------
step "Docker"

compose_file=$(ls docker-compose.yml compose.yml 2>/dev/null | head -n1 || true)
if [[ -z "$compose_file" ]]; then
    skip "no compose file yet"
elif (( FAST )); then
    skip "compose validation (--fast)"
elif has docker; then
    if docker compose -f "$compose_file" config -q 2>/dev/null; then
        ok "$compose_file is valid"
    else
        fail "$compose_file is invalid — run: docker compose config"
    fi
else
    skip "docker not installed"
fi

# ---------------------------------------------------------------------------
step "Documentation and metadata"

for doc in functional_design.md architecture.md technical_design.md CLAUDE.md; do
    [[ -f "$doc" ]] && ok "$doc present" || fail "$doc is missing"
done

if [[ -f VERSION ]]; then
    if grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' VERSION; then
        ok "VERSION is valid semver ($(cat VERSION))"
    else
        fail "VERSION does not parse as semver: $(cat VERSION)"
    fi
else
    fail "VERSION is missing"
fi

if [[ -f CHANGELOG.md ]]; then
    grep -q '## \[Unreleased\]' CHANGELOG.md \
        && ok "CHANGELOG has an Unreleased section" \
        || fail "CHANGELOG.md is missing its '## [Unreleased]' section"
else
    fail "CHANGELOG.md is missing"
fi

# ---------------------------------------------------------------------------
printf '\n'
if (( ${#SKIPPED[@]} > 0 )); then
    printf '%s%d check(s) skipped:%s %s\n' "$yellow" "${#SKIPPED[@]}" "$reset" "$(IFS=';'; echo "${SKIPPED[*]}" | sed 's/;/, /g')"
fi

if (( FAILED )); then
    printf '%s%sVERIFICATION FAILED%s\n' "$bold" "$red" "$reset"
    exit 1
fi

printf '%s%sVERIFICATION PASSED%s\n' "$bold" "$green" "$reset"
