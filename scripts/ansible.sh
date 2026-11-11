#!/usr/bin/env bash
#
# Run one of the playbooks in ansible/.
#
#   scripts/ansible.sh provision                 bare host → ready to run the stack
#   scripts/ansible.sh deploy                    ship the commit you are on
#   scripts/ansible.sh update                    OS patches, fresh images, redeploy
#   scripts/ansible.sh backup                    install the nightly backup
#   scripts/ansible.sh restore                   bring a backup back onto a host
#
#   scripts/ansible.sh -I disposable deploy      against the rehearsal VM (scripts/vm.sh)
#   scripts/ansible.sh deploy --check --diff     anything after the name goes to Ansible
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

args=(-i "inventory/${INVENTORY}")
vault="inventory/${INVENTORY}/group_vars/all/vault.yml"
if [[ -f "$vault" ]] && head -n1 "$vault" | grep -q ANSIBLE_VAULT; then
    if [[ -f .vault-pass ]]; then
        args+=(--vault-password-file .vault-pass)
    else
        args+=(--ask-vault-pass)
    fi
fi

echo "==> ${PLAYBOOK} (${INVENTORY})"
exec ansible-playbook "${args[@]}" "playbooks/${PLAYBOOK}.yml" "$@"
