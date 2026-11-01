#!/usr/bin/env bash
set -euo pipefail
name=${1:?Usage: start-windows.sh GUEST_NAME}
[[ $name =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ ]] || exit 2
# shellcheck source=oci/scripts/lab-common.sh
source "$(dirname "$0")/lab-common.sh"
"${lab_ssh[@]}" "sudo /usr/local/sbin/lab-guest start '$name'"
echo "Private RDP: $lab_ip:3389"
