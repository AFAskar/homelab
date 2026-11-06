#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export ANSIBLE_CONFIG="$PWD/homelab/ansible/ansible.cfg"

# Hyphens in these filenames prevent unittest discovery from importing them.
for test in homelab/scripts/test-*.py; do
  python "$test"
done

ansible-lint --profile production homelab/ansible/*.yaml docker/adguardhome/deploy.yaml
for playbook in homelab/ansible/*.yaml docker/adguardhome/deploy.yaml; do
  # inventory.yaml is data, rather than a playbook.
  if [[ "$playbook" != homelab/ansible/inventory.yaml ]]; then
    ansible-playbook --syntax-check "$playbook"
  fi
done
