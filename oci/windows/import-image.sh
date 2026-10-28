#!/usr/bin/env bash
set -euo pipefail
: "${OCI_APPROVE_IMAGE_IMPORT:?Set to yes only after explicit approval of image/upload storage spend}"
[[ $OCI_APPROVE_IMAGE_IMPORT == yes ]] || exit 2
: "${OCI_WIN11_COMPATIBILITY_EVIDENCE:?Supply reviewed supported Windows 11 custom-image TPM/UEFI evidence}"
[[ -f $OCI_WIN11_COMPATIBILITY_EVIDENCE ]] || exit 2
: "${OCI_COMPARTMENT_OCID:?}" "${OCI_IMAGE_BUCKET:?}" "${OCI_IMAGE_NAMESPACE:?}"
[[ $# == 1 && -f $1 ]] || { echo 'Usage: import-image.sh generalized.qcow2' >&2; exit 2; }
digest=$(sha256sum "$1" | cut -d' ' -f1)
: "${OCI_APPROVED_IMAGE_SHA256:?Supply the finalized image SHA256 recorded in the approved import plan}"
[[ $OCI_APPROVED_IMAGE_SHA256 =~ ^[0-9a-f]{64}$ && $digest == "$OCI_APPROVED_IMAGE_SHA256" ]] || { echo 'Image differs from the approved SHA256; stop and review it again.' >&2; exit 2; }
object="win11-$digest.qcow2"
image_name="win11-lab-$digest"
# A failed/timed-out import must resume the same image, never create a duplicate.
images=$(oci compute image list --compartment-id "$OCI_COMPARTMENT_OCID" --display-name "$image_name" --all)
# OCI CLI emits no JSON when a list is empty.
images=${images:-'{"data":[]}'}
image_id=$(python3 -c '
import json,sys
images=[i for i in json.load(sys.stdin)["data"] if i["display-name"]==sys.argv[1] and i["lifecycle-state"]!="TERMINATED"]
if len(images)>1: raise SystemExit("Multiple matching images; reconcile manually without deleting automatically.")
if images and images[0]["lifecycle-state"] not in ["AVAILABLE","IMPORTING"]: raise SystemExit("Existing image failed or is unavailable; inspect it before retrying.")
print(images[0]["id"] if images else "")
' "$image_name" <<< "$images")
if [[ -n $image_id ]]; then
  deadline=$((SECONDS + 7200))
  while (( SECONDS < deadline )); do
    state=$(oci compute image get --image-id "$image_id" --query 'data."lifecycle-state"' --raw-output)
    case "$state" in
      AVAILABLE) printf '%s\n' "$image_id"; exit 0 ;;
      IMPORTING) sleep 30 ;;
      *) echo "Existing image entered state $state; inspect before retrying." >&2; exit 2 ;;
    esac
  done
  echo "Timed out waiting for $image_id; rerun to resume without creating another image." >&2
  exit 1
fi
objects=$(oci os object list --namespace-name "$OCI_IMAGE_NAMESPACE" --bucket-name "$OCI_IMAGE_BUCKET" --prefix "$object" --all)
objects=${objects:-'{}'}
exists=$(python3 -c 'import json,sys; print(any(x["name"]==sys.argv[1] for x in (json.load(sys.stdin).get("data") or [])))' "$object" <<< "$objects")
if [[ $exists == True ]]; then
  stored_digest=$(oci os object head --namespace-name "$OCI_IMAGE_NAMESPACE" --bucket-name "$OCI_IMAGE_BUCKET" --name "$object" --query '"opc-meta-sha256"' --raw-output)
  [[ $stored_digest == "$digest" ]] || { echo 'Existing object lacks matching SHA256 metadata; inspect it manually.' >&2; exit 2; }
else
  oci os object put --namespace-name "$OCI_IMAGE_NAMESPACE" --bucket-name "$OCI_IMAGE_BUCKET" --name "$object" --file "$1" --no-overwrite --metadata "{\"sha256\":\"$digest\"}"
fi
source_details=$(python3 - "$OCI_IMAGE_NAMESPACE" "$OCI_IMAGE_BUCKET" "$object" <<'ENDPY'
import json,sys
print(json.dumps(dict(sourceType='objectStorageTuple',namespaceName=sys.argv[1],bucketName=sys.argv[2],objectName=sys.argv[3],sourceImageType='QCOW2')))
ENDPY
)
oci compute image create --compartment-id "$OCI_COMPARTMENT_OCID" --display-name "$image_name" --operating-system Windows --operating-system-version Windows11 \
  --launch-mode PARAVIRTUALIZED --image-source-details "$source_details" --wait-for-state AVAILABLE --max-wait-seconds 7200 --query data.id --raw-output
# Do not delete source images automatically. Import does not prove guest compatibility.
# Serialize runs for the same source disk; this is retry-safe, not a distributed lock.
