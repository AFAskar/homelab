#!/usr/bin/env python3
"""Reject destruction in a saved Terraform JSON plan. Does not authorize apply."""
import json, sys
plan = json.load(sys.stdin)
bad = [r['address'] for r in plan.get('resource_changes', []) if 'delete' in r['change']['actions']]
if bad:
    print('BLOCKED destructive/replacement actions: ' + ', '.join(bad), file=sys.stderr)
    sys.exit(1)
print('No delete/replacement actions found; review updates, costs and approvals separately.')
