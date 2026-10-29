#!/usr/bin/env bash
set -euo pipefail
# Post-import metadata only. Never launches an instance or changes a source VM.
[[ $# == 1 ]] || { echo 'Usage: configure-image.sh imported-image-ocid' >&2; exit 2; }
: "${OCI_APPROVE_IMAGE_IMPORT:?Use yes only within an explicitly approved image-import operation}"
[[ $OCI_APPROVE_IMAGE_IMPORT == yes ]] || exit 2
image_id=$1
root=$(cd "$(dirname "$0")" && pwd)
umask 077
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
oci compute image get --image-id "$image_id" > "$work/image.json"
compartment=$(python3 - "$work/image.json" <<'PY'
import json,sys
image=json.load(open(sys.argv[1]))['data']
if (image['lifecycle-state'] != 'AVAILABLE' or image['operating-system'] != 'Windows'
        or image['operating-system-version'] not in ['Windows11','Windows 11']):
    raise SystemExit('An available Windows 11 custom image is required; do not relabel another OS.')
if image['size-in-mbs'] > 100*1024:
    raise SystemExit('Image exceeds the approved 100GB boot allocation; stop and review.')
print(image['compartment-id'])
PY
)
oci compute image-capability-schema list --image-id "$image_id" --compartment-id "$compartment" --all > "$work/schemas.json"
# Preserve unrelated existing capability overrides when updating.
schema_id=$(python3 - "$work/schemas.json" "$root/image-capabilities.json" "$work/schema.json" <<'PY'
import json,sys
text=open(sys.argv[1]).read().strip()
items=json.loads(text)['data'] if text else []
if len(items)>1: raise SystemExit('Multiple image schemas; reconcile manually.')
schema=items[0].get('schema-data',{}) if items else {}
# OCI CLI responses use kebab-case; complex input descriptors use camelCase.
schema={key:{ {'descriptor-type':'descriptorType','default-value':'defaultValue'}.get(k,k):v for k,v in value.items()} for key,value in schema.items()}
schema.update(json.load(open(sys.argv[2])))
json.dump(schema,open(sys.argv[3],'w'))
print(items[0]['id'] if items else '')
PY
)
if [[ -z $schema_id ]]; then
  global_version=$(oci compute global-image-capability-schema list --all --query 'data[0]."current-version-name"' --raw-output)
  [[ -n $global_version && $global_version != null ]] || { echo 'Cannot determine the current global image schema version.' >&2; exit 2; }
fi
oci compute image update --image-id "$image_id" --operating-system-version Windows11 --force >/dev/null
if [[ -n $schema_id ]]; then
  oci compute image-capability-schema update --image-capability-schema-id "$schema_id" --schema-data "file://$work/schema.json" --force
else
  oci compute image-capability-schema create --image-id "$image_id" --compartment-id "$compartment" --global-image-capability-schema-version-name "$global_version" --schema-data "file://$work/schema.json"
fi
oci compute image-shape-compatibility-entry add --image-id "$image_id" --shape-name VM.Standard.E4.Flex --force
# Metadata acceptance is not a successful boot. Verify TPM2, Secure Boot, drivers
# and private RDP after the approved Terraform first launch. Open the gate only
# after reviewing accepted image/shape capabilities and the boot-volume minimum.
