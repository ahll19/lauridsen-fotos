#!/usr/bin/env bash
#
# Points git at the version-controlled hooks in .githooks/.
#
# Run once per clone. Hooks live in the repository rather than in .git/hooks so they are
# reviewed, versioned, and identical for everyone who works on this.
#
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

chmod +x .githooks/* scripts/*.sh
git config core.hooksPath .githooks

echo "✓ Hooks installed (core.hooksPath = .githooks)"
echo
echo "  pre-commit  runs scripts/verify.sh --fast"
echo "  commit-msg  enforces Conventional Commits"
echo "  pre-push    refuses direct pushes to main"
