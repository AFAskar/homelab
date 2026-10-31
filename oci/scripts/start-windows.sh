#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=oci/scripts/windows-common.sh
source "$(dirname "$0")/windows-common.sh"
state=$(oci compute instance get --instance-id "$windows_id" --query 'data."lifecycle-state"' --raw-output)
if [[ $state == RUNNING ]]; then
  printf 'win11-lab already %s\n' "$state"
  exit 0
fi
: "${OCI_APPROVE_BILLABLE_START:?Set OCI_APPROVE_BILLABLE_START=yes only after explicit approval of compute spend}"
[[ $OCI_APPROVE_BILLABLE_START == yes ]] || exit 2
oci compute instance action --instance-id "$windows_id" --action START --wait-for-state RUNNING --max-wait-seconds 1200
