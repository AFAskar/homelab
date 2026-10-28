#!/usr/bin/env bash
set -euo pipefail
: "${OCI_APPROVE_IMAGE_IMPORT:?Set to yes only after explicit approval of image/upload storage spend}"
[[ $OCI_APPROVE_IMAGE_IMPORT == yes ]] || exit 2
: "${OCI_WIN11_COMPATIBILITY_EVIDENCE:?Supply reviewed supported Windows 11 custom-image TPM/UEFI evidence}"
[[ -f $OCI_WIN11_COMPATIBILITY_EVIDENCE ]] || exit 2
: "${OCI_COMPARTMENT_OCID:?}" "${OCI_IMAGE_BUCKET:?}" "${OCI_IMAGE_NAMESPACE:?}"
[[ $# == 1 && -f $1 ]] || { echo 'Usage: import-image.sh generalized.qcow2' >&2; exit 2; }
object="win11-$(sha256sum "$1" | cut -d' ' -f1).qcow2"
oci os object put --namespace-name "$OCI_IMAGE_NAMESPACE" --bucket-name "$OCI_IMAGE_BUCKET" --name "$object" --file "$1" --no-overwrite
oci compute image create --compartment-id "$OCI_COMPARTMENT_OCID" --display-name win11-lab \
  --launch-mode PARAVIRTUALIZED --image-source-details "$(python3 - "$OCI_IMAGE_NAMESPACE" "$OCI_IMAGE_BUCKET" "$object" <<'ENDPY'
import json,sys
print(json.dumps(dict(sourceType='objectStorageTuple',namespaceName=sys.argv[1],bucketName=sys.argv[2],objectName=sys.argv[3],sourceImageType='QCOW2')))
ENDPY
)" --wait-for-state AVAILABLE --query data.id --raw-output
# Do not delete source images automatically. Import does not prove guest compatibility.
