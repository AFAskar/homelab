# Machines

There are three k3s server/agent nodes with embedded etcd: pos, optiplex and rpi4.
POS and rpi4 also provide DNS and the shared LAN API/DNS address 192.168.1.250.

## pos:

responsibilities: podman, control plane, agent node and DNS
ips: 192.168.1.28 (lan), 100.114.113.82 (tailscale)
distro: alma linux
username: pos
ssh config alias : pos
## optiplex

responsibilities: control plane and agent node
ips: 192.168.1.27 (lan), 100.77.7.115 (tailscale)
distro: alpine linux (doas not sudo)
username: run-barry-run
ssh config alias : optiplex

## rpi4

Alpine ARM64 Raspberry Pi 4, approximately 4 GB RAM; control plane and native DNS.
SSH alias/user: `rpi4`;
use doas. Wi-Fi recovery: 192.168.1.18; wired interface eth0 currently uses
192.168.1.23 statically. Keep static addresses outside router DHCP allocation.
Host automation is in `homelab/ansible/`; see `docs/homelab-ha.md`.
Retire foreign standalone state explicitly before joining a replacement node.

# Rootless Podman services

Use Quadlet for Ansible-managed persistent Podman services. AdGuard is managed
by `docker/adguardhome/deploy.yaml` and the user unit `adguardhome.service` on
`pos`:

```bash
ansible-playbook -i pos, docker/adguardhome/deploy.yaml
ssh pos 'systemctl --user status adguardhome.service'
ssh pos 'journalctl --user -u adguardhome.service -n 50 --no-pager'
```

For workloads that still use Compose, use `./remotepod.sh` from the repository
root. Do not use `podman compose` directly: its external provider drops the
SSH identity. The wrapper resolves the named connection's URI/identity and
disables pod creation for remote API compatibility. It defaults to connection
`pos`; set `PODMAN_CONNECTION` to use another named connection. Do not recreate
a Quadlet-managed service through Compose.

# Changes and commits

- Keep commits atomic: one coherent fix or feature per commit, including only its
  directly related documentation and validation changes.
- Validate each change before committing. Use a concrete commit message that
  explains the behavior changed; do not bundle unrelated review fixes.
- Keep review fixes simple and follow existing repository conventions.

# OCI Windows scope

For the OCI environment, Windows licensing is handled by the user and excluded
from infrastructure cost, feasibility and deployment analysis. Do not add
licensing costs or licensing approval gates. Keep technical image, firmware,
TPM, Secure Boot and access checks in scope.

# Documentation

- Write documentation as actionable setup, configuration, operations, checks
  and recovery instructions. Keep required inventory facts and dated pricing
  sources where they help operate the environment.
- Keep implementation summaries and relevant validation results in PR descriptions,
  not operator documentation. Put review discussion and incident timelines in
  appropriate comments rather than the PR description.
- Keep generated evidence, state, plans and raw run logs ignored and private.

# Publication privacy and PR attribution

- Treat information learned while inspecting the user's environment as private
  by default. Access to inspect a system is not permission to publish its details.
- Include only information directly necessary to implement, review or operate
  the change. Do not publish surrounding hardware identifiers, vendor/model or
  firmware details, unrelated network configuration, account information,
  screenshots, discovery notes or troubleshooting conversation in repository
  files, commit messages, PR descriptions or comments.
- Keep necessary deployment configuration scoped to the managed resources;
  describe external prerequisites generically. Keep environment-specific
  inspection evidence in ignored private storage. Ask before publishing private
  information when its disclosure is actually required for the requested work.
- Before committing or publishing, inspect the staged diff and outgoing PR text
  for unnecessary environment details. A PR must describe its change and relevant
  validation, not the surrounding environment or conversation history.
- Every PR created by the agent must state clearly in its description:
  "Created by Codex on behalf of @AFAskar."
  Preserve that attribution when updating the description; do not imply the user
  personally authored the agent's work.

# PR descriptions and review replies

- Describe the PR's resulting behavior and scope. Include validation performed,
  the observed results of any live validation, and relevant gaps outside scope.
  State the limits of the validation; do not imply service-outage tests prove
  whole-host or storage failover.
- Reply to CodeRabbit and other review findings in their original review threads,
  explaining the fix and relevant validation or why no change is warranted.
  For a finding outside a thread, post a comment linked to the original review.
- Do not put review-fix inventories, bot status, review conversations or responses
  to findings in the PR description. Preserve the required agent attribution.
