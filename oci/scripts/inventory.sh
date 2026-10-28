#!/usr/bin/env bash
# Read-only. Raw inventory is private and gitignored; permission failures remain visible.
set -euo pipefail
umask 077
: "${OCI_TENANCY_OCID:?Set OCI_TENANCY_OCID from the authenticated OCI profile}"
command -v oci >/dev/null || { echo 'Install OCI CLI and configure an API-key/session profile.' >&2; exit 2; }
out=${1:-"$(dirname "$0")/../inventory/$(date -u +%Y%m%dT%H%M%SZ)"}
mkdir -p "$out"
run() {
  local file=$1
  shift
  if ! oci "$@" > "$out/$file.json" 2> "$out/$file.error"; then
    printf 'FAILED: %s (see %s/%s.error)\n' "$file" "$out" "$file" >&2
    failures=$((failures + 1))
  fi
}
failures=0
run regions iam region-subscription list --tenancy-id "$OCI_TENANCY_OCID" --all
run compartments iam compartment list --compartment-id "$OCI_TENANCY_OCID" --compartment-id-in-subtree true --access-level ACCESSIBLE --all
run groups iam group list --compartment-id "$OCI_TENANCY_OCID" --all
run dynamic-groups iam dynamic-group list --compartment-id "$OCI_TENANCY_OCID" --all
run namespace os ns get
python3 - "$out" "$OCI_TENANCY_OCID" <<'ENDPY' > "$out/compartment-ids"
import json,pathlib,sys
p=pathlib.Path(sys.argv[1])/'compartments.json'
print(sys.argv[2])
if p.stat().st_size:
 for c in json.loads(p.read_text())['data']:
  if c['lifecycle-state']=='ACTIVE':print(c['id'])
ENDPY
while read -r region; do
  export OCI_CLI_REGION=$region
  while read -r compartment; do
    prefix="$region-${compartment##*.}"
    run "$prefix-ads" iam availability-domain list --compartment-id "$compartment" --all
    run "$prefix-policy" iam policy list --compartment-id "$compartment" --all
    for kind in instance vcn subnet internet-gateway nat-gateway service-gateway route-table security-list network-security-group public-ip; do
      args=()
      [[ $kind == public-ip ]] && args=(--scope REGION)
      # CLI has separate compute/network groups.
      group=network
      [[ $kind == instance ]] && group=compute
      [[ $kind == network-security-group ]] && kind=nsg
      run "$prefix-${kind/nsg/network-security-group}" "$group" "$kind" list --compartment-id "$compartment" "${args[@]}" --all
    done
    run "$prefix-volumes" bv volume list --compartment-id "$compartment" --all
    run "$prefix-attachments" compute volume-attachment list --compartment-id "$compartment" --all
    run "$prefix-vnics" compute vnic-attachment list --compartment-id "$compartment" --all
    while IFS= read -r vnic; do
      run "$prefix-vnic-${vnic##*.}" network vnic get --vnic-id "$vnic"
      run "$prefix-private-ips-${vnic##*.}" network private-ip list --vnic-id "$vnic" --all
    done < <(python3 -c 'import json,sys; print("\n".join(x["vnic-id"] for x in json.load(open(sys.argv[1]))["data"] if x.get("vnic-id")))' "$out/$prefix-vnics.json")
    while IFS= read -r nsg; do
      run "$prefix-nsg-rules-${nsg##*.}" network nsg rules list --nsg-id "$nsg" --all
    done < <(python3 -c 'import json,sys; print("\n".join(x["id"] for x in json.load(open(sys.argv[1]))["data"]))' "$out/$prefix-network-security-group.json")
    run "$prefix-images" compute image list --compartment-id "$compartment" --all
    run "$prefix-buckets" os bucket list --compartment-id "$compartment" --all
    run "$prefix-quotas" limits quota list --compartment-id "$compartment" --all
    run "$prefix-compute-limits" limits value list --compartment-id "$OCI_TENANCY_OCID" --service-name compute --all
    while IFS= read -r ad; do
      adkey=${ad//[^a-zA-Z0-9]/_}
      run "$prefix-$adkey-shapes" compute shape list --compartment-id "$compartment" --availability-domain "$ad" --all
      run "$prefix-$adkey-boot" bv boot-volume list --compartment-id "$compartment" --availability-domain "$ad" --all
      run "$prefix-$adkey-boot-attachments" compute boot-volume-attachment list --compartment-id "$compartment" --availability-domain "$ad" --all
    done < <(python3 -c 'import json,sys; print("\n".join(x["name"] for x in json.load(open(sys.argv[1]))["data"]))' "$out/$prefix-ads.json")
  done < "$out/compartment-ids"
done < <(python3 -c 'import json,sys; print("\n".join(x["region-name"] for x in json.load(open(sys.argv[1]))["data"]))' "$out/regions.json")
printf 'Inventory saved privately in %s; failed queries: %d\n' "$out" "$failures"
(( failures == 0 ))
