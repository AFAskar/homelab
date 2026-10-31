#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=oci/scripts/windows-common.sh
source "$(dirname "$0")/windows-common.sh"
state=$(oci compute instance get --instance-id "$windows_id" --query 'data."lifecycle-state"' --raw-output)
if [[ $state == STOPPED ]]; then
  printf 'win11-lab already %s\n' "$state"
  exit 0
fi
oci compute instance action --instance-id "$windows_id" --action SOFTSTOP --wait-for-state STOPPED --max-wait-seconds 1200
