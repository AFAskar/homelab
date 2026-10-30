# AdGuard Home as code

The container already used `docker/adguardhome.yaml`. Its host-only settings,
firewall redirects and boot prerequisites were previously manual. The complete
service now reconciles through `docker/adguardhome/deploy.yaml`, preserving
its existing rootless Podman/pasta deployment and persistent data paths.

## Sources and deployment

- `docker/adguardhome.yaml`: pinned image, restart policy, address-bound ports
  and existing work/config mounts. Address defaults remove manual exports.
- `docker/adguardhome/AdGuardHome.secret.sops.yaml`: authoritative complete
  configuration encrypted with the existing repository age recipient,
  including the existing account/password hash, upstreams, filters and rules.
- `kubernetes/pelican/manifests/wings-endpoints.yaml`: desired Wings private
  addresses, also consumed by monitoring. Deployment derives exact DNS rules
  from these endpoints, avoiding another copy of changing OCI addresses.
- `docker/adguardhome/podman-restart.override.conf`: the existing Tailscale-aware
  rootless boot ordering, now versioned.
- `oci/ansible/dns.yaml`: imports the same deployment; it no longer patches the
  live settings independently.

Use the existing pos SSH/sudo access, named Podman connection `pos`, and SOPS
age identity from the established PKI recovery workflow. These are credential
bootstrap prerequisites; do not put identities or plaintext settings in Git.
The operator needs Ansible, SOPS, Podman/podman-compose and dig. Install the
repository's pinned collections if necessary:

```bash
ansible-galaxy collection install -r oci/ansible/requirements.yaml
ansible-playbook -i pos, docker/adguardhome/deploy.yaml
```

The existing OCI workflow also works:

```bash
cd oci/ansible
ansible-playbook dns.yaml
```

The playbook installs runtime/firewall prerequisites, ensures persistent
private directories, user lingering, Podman socket/restart-policy startup,
and the existing firewalld rules. It preserves both LAN and tailnet DNS
53-to-5353 redirects, direct LAN TCP/UDP 5353 and existing UI bindings.
It never reloads the whole firewall or restarts unrelated containers.
Compose operations use `./remotepod.sh`, as required by AGENTS.md.

Desired settings are decrypted in operator memory and validated using the
pinned AdGuard binary in an isolated disposable container before changing the
running resolver. Temporary plaintext is private and removed afterward.
Semantic YAML comparison avoids restarts caused only by formatting. On actual
configuration drift, the prior file is preserved once as a private
`.before-iac` backup, AdGuard is stopped before writing settings, and Compose
is converged in an `always` block. No query/statistics data is deleted.
Editing while AdGuard is running can be overwritten by the application;
see the [official Docker configuration instructions](https://github.com/AdguardTeam/AdGuardHome/wiki/Docker#additional-configuration).

Public/internal resolution and each exact Wings answer are checked after
convergence. The native `--check-config` check also rejects malformed desired
settings before DNS is stopped. A fresh host with the credential/host-access
prerequisites can recreate the initialized service without the web wizard.
Query history, caches and statistics are runtime data, not configuration.

## Changes and recovery

Edit the encrypted source with `sops docker/adguardhome/AdGuardHome.secret.sops.yaml`,
review/commit the change and rerun deployment. The decrypted wrapper contains
`data.AdGuardHome.yaml` as a YAML string. Durable settings changes belong here;
manual web-UI edits are drift and will be replaced on reconciliation.
The imported credentials and upstream choices were preserved, not rotated.
No plaintext export or generated run report belongs in the repository.

After approved OCI address changes, run `render-inventory.py`, review the
updated desired EndpointSlice, and deploy DNS through either entrypoint.
Commit the desired target change for the normal GitOps workflow. CoreDNS
continues forwarding `home.internal` to pos:5353; no new resolver VM is used.

For recovery, retain the config/work volumes and use the reviewed source to
recreate the service. Restore any required runtime-data backup separately.
Keep SSH, the existing SOPS recovery identity and the named Podman connection
available independently of DNS. A rejected configuration leaves the running
resolver untouched. Investigate an actual Compose/start failure using its
private diagnostics and pre-IaC backup before retrying; do not wipe volumes.

## Validation — October 30, 2026

Production Ansible lint passes. The initial adoption preserved the running
container; a full rerun changed zero resources. Native validation accepted
the desired settings and rejected an invalid-port fixture without touching
live DNS. LAN public/internal and exact Wings answers passed. The encrypted
configuration uses the existing SOPS recipient; raw logs stay ignored.
A fresh-host rebuild and host reboot were not performed; current-host
convergence, native validation and boot configuration were verified.
The separate [outage investigation](dns-network-incident-2026-10-30.md) records
what the logs establish and what still requires router diagnostics.
