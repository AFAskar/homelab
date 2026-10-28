#!/usr/bin/env bash
set -euo pipefail
oci_tf_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../terraform" && pwd)
# Identity comes only from the configured Terraform backend, never a fuzzy name search.
windows_id=$(terraform -chdir="$oci_tf_root" output -raw windows_instance_id)
[[ $windows_id == ocid1.instance.* ]] || { echo 'No Terraform-managed Windows instance identity.' >&2; exit 2; }
# Avoid operating in a different configured region from the Terraform provider.
oci_region=$(terraform -chdir="$oci_tf_root" output -raw region)
oci_profile=$(terraform -chdir="$oci_tf_root" output -raw oci_profile)
export OCI_CLI_REGION=$oci_region OCI_CLI_PROFILE=$oci_profile
