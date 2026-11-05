#!/usr/bin/env bash
set -euo pipefail
[[ $# == 1 ]] || { echo "Usage: stop-windows.sh GUEST_NAME (the shared host stays running)" >&2; exit 2; }
name=${1:?Usage: stop-windows.sh GUEST_NAME }
[[ $name =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ ]] || exit 2
# shellcheck source=oci/scripts/lab-common.sh
source "$(dirname "$0")/lab-common.sh"
"${lab_ssh[@]}" "sudo /usr/local/sbin/lab-guest save '$name'"
echo "Windows RAM saved. Shared wings-02 remains running."
