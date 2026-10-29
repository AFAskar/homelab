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

# Remote Podman Compose

Use `./remotepod.sh` from the repository root for Compose workloads on `pos`.
Do not use `podman compose` directly because its external Compose provider drops
the SSH identity from the named Podman connection. The script resolves the
connection URI and identity, exports the required remote Podman environment,
and disables pod creation to avoid the remote pod API issue.

Examples:

```bash
./remotepod.sh -f docker/adguardhome.yaml ps
./remotepod.sh -f docker/adguardhome.yaml up -d
./remotepod.sh -f docker/adguardhome.yaml logs
```

The script uses the `pos` Podman connection by default. Set
`PODMAN_CONNECTION=<name>` to target another configured connection.

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
