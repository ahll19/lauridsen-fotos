#!/usr/bin/env bash
#
# Disposable machines for rehearsing the playbooks, so the real server is never the first
# place one is run. Needs Lima (brew install lima).
#
#   scripts/vm.sh up        a bare Debian 12 "VPS" and a second machine playing the NAS
#   scripts/vm.sh rebuild   throw the VPS away and start a bare one (the NAS is kept)
#   scripts/vm.sh ssh [nas] a shell on the VPS, or on the NAS
#   scripts/vm.sh status    what exists
#   scripts/vm.sh down      delete both
#
# `up` writes ansible/inventory/disposable/, which is gitignored: it holds this machine's
# SSH port and a set of throwaway secrets generated for the rehearsal. Then:
#
#   scripts/ansible.sh -I disposable provision
#   scripts/ansible.sh -I disposable deploy
#
# The rehearsal differs from production in one deliberate way. There is no real domain, so
# certificates come from Pebble — Let's Encrypt's own test server — running beside the
# stack. Everything else, certbot included, runs exactly as it will on the VPS.
#
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

HOST_VM=lf-host
NAS_VM=lf-nas
TEMPLATE=ansible/lima/debian12.yaml
INVENTORY=ansible/inventory/disposable
DOMAIN=fotos.test
BACKUP_PATH=/srv/backups/lauridsen-fotos

command -v limactl >/dev/null 2>&1 || { echo "Lima is not installed: brew install lima" >&2; exit 1; }

LIMA_KEY="${LIMA_HOME:-$HOME/.lima}/_config/user"
SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -i "$LIMA_KEY")

exists() { limactl list --format '{{.Name}}' 2>/dev/null | grep -qx "$1"; }
port()   { limactl list --format '{{.SSHLocalPort}}' "$1"; }
as_root() { local vm=$1; shift; ssh "${SSH_OPTS[@]}" -p "$(port "$vm")" root@127.0.0.1 "$@"; }

start() {
    if exists "$1"; then
        [[ "$(limactl list --format '{{.Status}}' "$1")" == Running ]] || limactl start "$1"
    else
        echo "==> Creating $1"
        limactl start --name="$1" --tty=false "$TEMPLATE"
    fi
}

write_inventory() {
    mkdir -p "$INVENTORY/group_vars/all"
    # Generated once and kept: regenerating would orphan the key the NAS already trusts.
    if [[ ! -f "$INVENTORY/group_vars/all/secrets.yml" ]]; then
        scripts/vault.sh generate >"$INVENTORY/group_vars/all/secrets.yml"
        chmod 600 "$INVENTORY/group_vars/all/secrets.yml"
    fi
    cat >"$INVENTORY/hosts.yml" <<EOF
# Written by scripts/vm.sh. The port changes every time the VM is recreated.
all:
  children:
    site:
      hosts:
        $HOST_VM:
          ansible_host: 127.0.0.1
          ansible_port: $(port "$HOST_VM")
  vars:
    ansible_ssh_private_key_file: "$LIMA_KEY"
    # A rebuilt VM has a new host key on the same address, by design.
    ansible_ssh_common_args: "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
EOF
    cat >"$INVENTORY/group_vars/all/vars.yml" <<EOF
# Written by scripts/vm.sh. The rehearsal's stand-ins for what production takes from
# ansible/inventory/production.
site_domain: $DOMAIN
site_alternate_domains:
  - www.$DOMAIN

operator_ssh_public_keys:
  - "$(cat "$LIMA_KEY.pub")"
# Lima manages the VM through its own account; shutting it out would strand the VM.
ssh_allow_users:
  - "{{ operator_user }}"
  - "$(id -un)"

# A domain that publishes a null MX record: mail addressed here is accepted by the relay
# and then goes nowhere, so a rehearsal cannot send anything to a real mailbox.
owner_email: owner@example.com

# Certificates from Pebble, Let's Encrypt's test server, started beside the stack by the
# extra compose file. Its API certificate is self-signed, hence --no-verify-ssl.
compose_extra_files:
  - ansible/lima/docker-compose.rehearsal.yml
letsencrypt_agree_tos: true
certbot_server: https://pebble:14000/dir
certbot_extra_args: --no-verify-ssl
certbot_retry_interval: 20
certbot_renew_interval: 60
cert_reload_interval: 5
healthcheck_verify_tls: false

backup_target_host: lima-$NAS_VM.internal
backup_target_user: backup
backup_target_path: $BACKUP_PATH

django_secret_key: "{{ vault_django_secret_key }}"
django_admin_path: "{{ vault_django_admin_path }}"
dkim_private_key: "{{ vault_dkim_private_key }}"
backup_ssh_private_key: "{{ vault_backup_ssh_private_key }}"
EOF
    echo "✓ Wrote $INVENTORY"
}

# The part of the rehearsal that is not ours to automate in production: an account on the
# NAS that accepts the backup key.
prepare_nas() {
    local key pub
    key=$(mktemp)
    # shellcheck disable=SC2064
    trap "rm -f '$key'" RETURN
    awk '/^vault_backup_ssh_private_key:/ {on=1; next} /^[^ ]/ {on=0} on && /^  / {sub(/^  /, ""); print}' \
        "$INVENTORY/group_vars/all/secrets.yml" >"$key"
    chmod 600 "$key"
    pub=$(ssh-keygen -y -f "$key")
    as_root "$NAS_VM" "
        set -e
        command -v rsync >/dev/null || { apt-get update -qq && apt-get install -y -qq rsync >/dev/null; }
        id backup >/dev/null 2>&1 && usermod -s /bin/sh -d /home/backup -m backup 2>/dev/null || true
        install -d -o backup -g backup -m 700 /home/backup /home/backup/.ssh
        echo '$pub' > /home/backup/.ssh/authorized_keys
        chown backup:backup /home/backup/.ssh/authorized_keys
        chmod 600 /home/backup/.ssh/authorized_keys
        install -d -o backup -g backup -m 700 '$BACKUP_PATH'
    "
    echo "✓ $NAS_VM accepts the backup key"
}

case "${1:-}" in
    up)
        start "$HOST_VM"
        start "$NAS_VM"
        write_inventory
        prepare_nas
        cat <<EOF

Rehearse with:
    scripts/ansible.sh -I disposable provision
    scripts/ansible.sh -I disposable deploy
    scripts/ansible.sh -I disposable backup -e backup_run_now=true
EOF
        ;;

    rebuild)
        exists "$HOST_VM" && limactl delete --force "$HOST_VM"
        start "$HOST_VM"
        write_inventory
        ;;

    ssh)
        vm=$HOST_VM
        [[ "${2:-}" == nas ]] && vm=$NAS_VM
        shift $(( $# > 1 ? 2 : 1 ))
        # As Lima's own account, which survives provisioning; root does not.
        ssh "${SSH_OPTS[@]}" -p "$(port "$vm")" "$(id -un)@127.0.0.1" "$@"
        ;;

    status)
        limactl list
        ;;

    down)
        for vm in "$HOST_VM" "$NAS_VM"; do
            exists "$vm" && limactl delete --force "$vm"
        done
        rm -rf "$INVENTORY"
        echo "✓ Removed the rehearsal machines and $INVENTORY"
        ;;

    *)
        echo "usage: scripts/vm.sh <up|rebuild|ssh [nas]|status|down>" >&2
        exit 2
        ;;
esac
