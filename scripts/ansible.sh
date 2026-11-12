#!/usr/bin/env bash
#
# Run one of the playbooks in ansible/.
#
#   scripts/ansible.sh provision                 bare host → ready to run the stack
#   scripts/ansible.sh deploy                    pull main onto the host and run it
#   scripts/ansible.sh update                    OS patches, fresh images, redeploy
#   scripts/ansible.sh backup                    install the nightly backup
#   scripts/ansible.sh restore                   bring a backup back onto a host
#
#   scripts/ansible.sh -I disposable deploy      against the rehearsal VM (scripts/vm.sh)
#   scripts/ansible.sh deploy --check --diff     anything after the name goes to Ansible
#
#   scripts/ansible.sh provision --first-run     the one run that logs in with passwords
#
# --first-run is for a host that does not have the operator's key yet. It asks for the
# operator's SSH password and for root's password, uses them for that run and stores
# neither. Provision installs the key and switches password logins off, so every later run
# needs no password at all (ADR 0011).
#
# Takes care of the three things that are otherwise easy to get wrong: running from the
# directory ansible.cfg lives in, installing the pinned collections, and handing over the
# vault password without it ever being typed into a command line.
#
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT/ansible"

INVENTORY=production
if [[ "${1:-}" == "-I" ]]; then
    INVENTORY="${2:?-I needs an inventory name}"
    shift 2
fi

PLAYBOOK="${1:-}"
if [[ -z "$PLAYBOOK" || ! -f "playbooks/${PLAYBOOK}.yml" ]]; then
    echo "usage: scripts/ansible.sh [-I <inventory>] <playbook> [ansible-playbook arguments]" >&2
    echo "playbooks: $(find playbooks -maxdepth 1 -name '*.yml' -exec basename {} .yml \; | sort | tr '\n' ' ')" >&2
    exit 2
fi
shift

# Bash 3.2 (macOS) treats an empty array as unset, hence the ${x[@]+...} below.
FIRST_RUN=0
rest=()
for arg in "$@"; do
    if [[ "$arg" == --first-run ]]; then FIRST_RUN=1; else rest+=("$arg"); fi
done

if [[ ! -d "inventory/${INVENTORY}" ]]; then
    echo "No inventory at ansible/inventory/${INVENTORY}." >&2
    [[ "$INVENTORY" == disposable ]] && echo "Create the rehearsal VM first: scripts/vm.sh up" >&2
    exit 1
fi

# The project's own virtualenv if there is one, otherwise whatever is installed.
[[ -x "$ROOT/.venv/bin/ansible-playbook" ]] && PATH="$ROOT/.venv/bin:$PATH"
if ! command -v ansible-playbook >/dev/null 2>&1; then
    echo "Ansible is not installed. In the repository root:" >&2
    echo "    python3 -m venv .venv && .venv/bin/pip install ansible-core ansible-lint" >&2
    exit 1
fi

# Reinstalled whenever requirements.yml is newer than the last install.
if [[ ! -f .collections/.installed || requirements.yml -nt .collections/.installed ]]; then
    echo "==> Installing the pinned collections"
    ansible-galaxy collection install -r requirements.yml -p .collections --force >/dev/null
    touch .collections/.installed
fi

if [[ "$INVENTORY" == production && ! -f inventory/production/group_vars/all/vault.yml ]]; then
    echo "There is no vault yet, so the playbooks have no secrets to give the host." >&2
    echo "Create it once with: scripts/vault.sh init" >&2
    exit 1
fi

args=(-i "inventory/${INVENTORY}")
if [[ "$FIRST_RUN" == 1 ]]; then
    # A password login goes through sshpass, which macOS does not ship.
    if ! command -v sshpass >/dev/null 2>&1; then
        echo "--first-run logs in with a password, and that needs sshpass:" >&2
        echo "    brew install sshpass" >&2
        exit 1
    fi
    # su rather than sudo: on a host that was installed with a root password, the first
    # account is not in sudoers. Add --become-method sudo after --first-run if yours is.
    args+=(--ask-pass --ask-become-pass --become-method su)
    # A login shell, so root gets its own PATH. Without it su keeps the operator's, which
    # has no sbin directory, and installing a package fails partway through.
    export ANSIBLE_SU_FLAGS=-l
fi
vault="inventory/${INVENTORY}/group_vars/all/vault.yml"
if [[ -f "$vault" ]] && head -n1 "$vault" | grep -q ANSIBLE_VAULT; then
    if [[ -f .vault-pass ]]; then
        args+=(--vault-password-file .vault-pass)
    else
        args+=(--ask-vault-pass)
    fi
fi

# The rehearsal VM pulls from a copy of this checkout rather than from GitHub; refresh it,
# so what is rehearsed is the commit that is checked out now.
if [[ "$INVENTORY" == disposable ]]; then
    "$ROOT/scripts/vm.sh" sync
fi

echo "==> ${PLAYBOOK} (${INVENTORY})"
if [[ "$FIRST_RUN" == 1 ]]; then
    echo "    First run: two passwords are asked for, used for this run and stored nowhere."
    echo "      SSH password     the operator account's password on the server"
    echo "      BECOME password  root's password on the server"
fi
exec ansible-playbook "${args[@]}" "playbooks/${PLAYBOOK}.yml" ${rest[@]+"${rest[@]}"}
