# Machines

there are 2 nodes in the homelab each equipped with k3s

## pos:

responsibilities: podman, control plane and agent node
ips: 192.168.1.28 (lan), 100.114.113.82 (tailscale)
distro: alma linux
username: pos
ssh config alias : pos
## optiplex

responsibilities: agent node
ips: 192.168.1.27 (lan), 100.77.7.115 (tailscale)
distro: alpine linux (doas not sudo)
username: run-barry-run
ssh config alias : optiplex

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
