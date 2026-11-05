#!/usr/bin/env python3
"""Check incremental compute quota and Ubuntu image compatibility for a saved plan."""
import argparse
import json
import os
from pathlib import Path


# Query only pools actually present in the plan; never require an unused shape.
LIMIT_POOLS = {
    'VM.Standard.E6.Flex': 'standard-e6',
    'VM.Standard.E4.Flex': 'standard-e4',
}


def requirements(plan, compute, compartment, ad):
    """Credit live, same-pool instances only; do not bank future releases."""
    pools = {}
    for resource in plan.get('resource_changes', []):
        if resource.get('mode', 'managed') != 'managed' or resource['type'] != 'oci_core_instance':
            continue
        change = resource['change']
        after = change.get('after')
        if after is None:  # Deletion does not establish reusable headroom yet.
            continue
        shape = after.get('shape')
        if shape not in LIMIT_POOLS:
            if change['actions'] != ['no-op']:
                raise ValueError(f"Unsupported or unknown compute shape at {resource['address']}; review its quota separately")
            continue  # The unchanged retained A1 instance needs no E-series quota.
        if after.get('compartment_id') != compartment or after.get('availability_domain') != ad:
            raise ValueError(f"Plan scope differs from --compartment/--ad at {resource['address']}")
        config = after.get('shape_config') or []
        if len(config) != 1 or any(config[0].get(k) is None for k in ['ocpus', 'memory_in_gbs']):
            raise ValueError(f"Unknown planned allocation at {resource['address']}; generate a complete plan")
        desired = {'core': float(config[0]['ocpus']), 'memory': float(config[0]['memory_in_gbs'])}
        if any(value <= 0 for value in desired.values()):
            raise ValueError(f"Invalid planned allocation at {resource['address']}")
        current = {'core': 0, 'memory': 0}
        before = change.get('before') or {}
        # Replacements may need both instances simultaneously. Require full new
        # capacity rather than assuming destroy ordering or crediting a release.
        if not {'create', 'delete'} & set(change['actions']):
            instance_id = before.get('id')
            if not instance_id or after.get('id') != instance_id:
                raise ValueError(f"Missing retained identity at {resource['address']}; refresh the plan")
            instance = compute.get_instance(instance_id).data
            if instance.lifecycle_state not in {'RUNNING', 'STOPPED', 'STARTING', 'STOPPING'}:
                raise ValueError(f"Instance is not in a stable allocated lifecycle at {resource['address']}; refresh the plan")
            if (instance.shape, instance.compartment_id, instance.availability_domain) == (shape, compartment, ad):
                current = {'core': instance.shape_config.ocpus, 'memory': instance.shape_config.memory_in_gbs}
                if any(value is None or value <= 0 for value in current.values()):
                    raise ValueError(f"Unknown live allocation at {resource['address']}")
        pool = pools.setdefault(shape, {key: {'desired': 0, 'existing': 0, 'needed': 0} for key in desired})
        for key, target in desired.items():
            pool[key]['desired'] += target
            pool[key]['existing'] += current[key]
            # Per-instance positive deltas prevent a planned downsize elsewhere
            # from hiding headroom needed before that capacity is released.
            pool[key]['needed'] += max(0, target - current[key])
    if not pools:
        raise ValueError('Plan contains no supported paid compute allocations')
    return pools


def quota_checks(pools, limits, compartment, ad):
    checks = []
    for shape, resources in sorted(pools.items()):
        for kind, demand in resources.items():
            name = LIMIT_POOLS[shape] + '-' + kind + '-count'
            available = None
            if demand['needed']:
                result = limits.get_resource_availability('compute', name, compartment, availability_domain=ad).data
                available = result.fractional_availability if result.fractional_availability is not None else result.available
            checks.append({'shape': shape, 'limit': name, **demand, 'available': available,
                           'pass': demand['needed'] == 0 or available is not None and available >= demand['needed']})
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compartment', required=True)
    parser.add_argument('--ad', required=True)
    parser.add_argument('--ubuntu-image', required=True)
    parser.add_argument('--plan-json', type=Path, required=True,
                        help='Private JSON from terraform show -json of the reviewed saved plan')
    args = parser.parse_args()
    import oci
    config = oci.config.from_file(profile_name=os.environ.get('OCI_CLI_PROFILE', 'DEFAULT'))
    compute = oci.core.ComputeClient(config)
    limits = oci.limits.LimitsClient(config)
    pools = requirements(json.loads(args.plan_json.read_text()), compute, args.compartment, args.ad)
    image = compute.get_image(args.ubuntu_image).data
    if image.operating_system != 'Canonical Ubuntu' or image.operating_system_version != '26.04' or 'aarch64' in image.display_name:
        raise ValueError('Expected exact Ubuntu 26.04 x86-64 image; no fallback permitted.')
    compute.get_image_shape_compatibility_entry(args.ubuntu_image, 'VM.Standard.E6.Flex')
    checks = quota_checks(pools, limits, args.compartment, args.ad)
    print(json.dumps({'image': image.display_name, 'quota_checks': checks,
                      'notice': 'Needed is additional capacity after verified live allocations. Zero demand needs no availability query. Planned releases are not credited; replacements require full new capacity. Does not reserve physical capacity, establish free entitlements, or authorize deployment.'}, indent=2))
    return 0 if all(check['pass'] for check in checks) else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except ValueError as error:
        raise SystemExit(str(error)) from None
