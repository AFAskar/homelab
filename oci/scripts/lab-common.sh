#!/usr/bin/env bash
set -euo pipefail
oci_tf_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../terraform" && pwd)
lab_json=$(terraform -chdir="$oci_tf_root" output -json lab_host)
lab_id=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$lab_json")
lab_ip=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["private_ip"])' <<<"$lab_json")
[[ $lab_id == ocid1.instance.* ]] || { echo 'No Terraform-managed lab host.' >&2; exit 2; }
export OCI_CLI_REGION OCI_CLI_PROFILE
OCI_CLI_REGION=$(terraform -chdir="$oci_tf_root" output -raw region)
OCI_CLI_PROFILE=$(terraform -chdir="$oci_tf_root" output -raw oci_profile)
# Used by the scripts that source this file.
# shellcheck disable=SC2034
lab_ssh=(ssh -i "${LAB_SSH_KEY:-$HOME/.ssh/KaliVM}" -o IdentitiesOnly=yes -o BatchMode=yes "ubuntu@$lab_ip")

shared=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["shared_with_wings"])' <<<"$lab_json")
[[ $shared == True ]] || { echo "Expected the shared wings-02 host." >&2; exit 2; }
