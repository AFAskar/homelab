#!/usr/bin/env bash
# Back up an already quiesced, explicitly selected archive to the private bucket.
set -euo pipefail
: "${BACKUP_QUIESCED:?Set BACKUP_QUIESCED=yes after stopping selected game servers or making a SQLite-consistent Panel backup}"
[[ $BACKUP_QUIESCED == yes && $# == 1 && -f $1 ]] || exit 2
root=$(cd "$(dirname "$0")/../terraform" && pwd)
namespace=$(terraform -chdir="$root" output -json backup_bucket | python3 -c 'import json,sys; print(json.load(sys.stdin)["namespace"])')
bucket=$(terraform -chdir="$root" output -json backup_bucket | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')
export OCI_CLI_REGION
OCI_CLI_REGION=$(terraform -chdir="$root" output -raw region)
export OCI_CLI_PROFILE
OCI_CLI_PROFILE=$(terraform -chdir="$root" output -raw oci_profile)
object="selected/$(date -u +%Y%m%dT%H%M%SZ)-$(basename "$1")"
oci os object put --namespace-name "$namespace" --bucket-name "$bucket" --name "$object" --file "$1" --no-overwrite
sha256sum "$1"
printf 'Restore object: %s\n' "$object"
