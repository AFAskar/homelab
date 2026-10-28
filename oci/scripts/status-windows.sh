#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=oci/scripts/windows-common.sh
source "$(dirname "$0")/windows-common.sh"
oci compute instance get --instance-id "$windows_id" --query 'data.{name:"display-name",state:"lifecycle-state",shape:shape}'
