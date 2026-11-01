#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=oci/scripts/lab-common.sh
source "$(dirname "$0")/lab-common.sh"
oci compute instance get --instance-id "$lab_id" --query 'data.{name:"display-name",state:"lifecycle-state",shape:shape}'
state=$(oci compute instance get --instance-id "$lab_id" --query 'data."lifecycle-state"' --raw-output)
if [[ $state != RUNNING ]]; then echo 'Shared host is not running; live guest state is unknown. No host action was performed.'; exit 0; fi
name=${1:?Usage: status-windows.sh GUEST_NAME}
[[ $name =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ ]] || exit 2
"${lab_ssh[@]}" "sudo /usr/local/sbin/lab-guest status '$name'"
