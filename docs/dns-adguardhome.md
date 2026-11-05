# AdGuard Home

AdGuard runs on pos as the rootless systemd user service `adguardhome.service`.
Ansible installs its Quadlet, encrypted configuration, persistent directories
and DNS firewall rules.

## Deploy

Prerequisites: SSH/sudo access to pos, Ansible, SOPS, dig and the repository's
SOPS age identity. Load the identity using the PKI recovery procedure; keep it
outside Git. Install the pinned collections and deploy from the repository root:

```bash
ansible-galaxy collection install -r oci/ansible/requirements.yaml
ansible-playbook -i pos, docker/adguardhome/deploy.yaml
```

The OCI DNS entrypoint runs the same deployment:

```bash
cd oci/ansible
ansible-playbook dns.yaml
```

Sources:

| File | Purpose |
|---|---|
| `docker/adguardhome/adguardhome.container.j2` | Image, network, ports, mounts and systemd restart/boot policy |
| `docker/adguardhome/AdGuardHome.secret.sops.yaml` | Complete private settings, upstreams, filters and account credentials |
| `kubernetes/pelican/manifests/wings-endpoints.yaml` | Wings addresses used to derive exact DNS records |

The rendered Quadlet lives at `~pos/.config/containers/systemd/adguardhome.container`.
Its `[Install] WantedBy=default.target` section and user lingering provide boot
activation. Systemd owns container restarts. AdGuard uses pasta networking and
its existing bind mounts:

- `/home/pos/.config/adguardhome`: configuration.
- `/home/pos/apps/docker/adguardhome`: query history, filter caches and statistics.

LAN/tailnet DNS port 53 is forwarded to the rootless listener on 5353. The web
interface binds to the configured LAN/tailnet addresses on 3000. Settings and
the candidate Quadlet are validated before the running resolver is changed.
An actual settings change stops the service before writing, saves a private
backup and starts the service again. Formatting-only differences do not
restart it.

## Operate and check

Run service commands through the pos account:

```bash
ssh pos 'systemctl --user status adguardhome.service'
ssh pos 'systemctl --user restart adguardhome.service'
ssh pos 'journalctl --user -u adguardhome.service -n 50 --no-pager'
dig @192.168.1.28 github.com
dig +tcp @192.168.1.28 pelican.home.internal
dig @100.114.113.82 wings-01.oci.home.internal
```

If DNS fails, check host reachability, the service journal, port bindings and
firewalld redirects before changing the application configuration. Compare
`dig @192.168.1.28 -p 5353 github.com` with the port-53 query to distinguish the
container listener from host forwarding. Preserve logs privately.

## Change settings or addresses

```bash
sops docker/adguardhome/AdGuardHome.secret.sops.yaml
ansible-playbook -i pos, docker/adguardhome/deploy.yaml
```

Edit the YAML string under `data.AdGuardHome.yaml`, then commit the encrypted
change. Web-UI settings edits are drift and will be replaced on reconciliation.
Keep plaintext exports and runtime data outside Git.

After OCI address changes, run `python3 oci/scripts/render-inventory.py`, review
the desired EndpointSlice and redeploy DNS. CoreDNS forwards `home.internal`
to pos:5353. Each Wings name must resolve to exactly its private VNIC address.
For image upgrades, update `adguard_image` in the deployment playbook,
check configuration compatibility, and deploy after preserving required data.

## Migration and recovery

The playbook recognizes the old Compose container, stops it, disables its
restart policy and retains it as `adguardhome-compose-retained`. A failed
initial migration restores that container. It refuses to overwrite an
existing retained container or take over an unrelated container name.
Other Podman services are not reconfigured.

For normal recovery, correct/revert the source and rerun deployment. Restore
a needed configuration backup from the private config directory while the
service is stopped. Keep the work directory for history/statistics; a service
restart or recreation does not require wiping it.

For emergency rollback to the retained Compose container, run on pos:

```bash
systemctl --user stop adguardhome.service
mv ~/.config/containers/systemd/adguardhome.container \
   ~/.config/containers/systemd/adguardhome.container.disabled
systemctl --user daemon-reload
podman rename adguardhome-compose-retained adguardhome
rollback_label=$(podman inspect --format '{{.MountLabel}}' adguardhome)
if [ -n "$rollback_label" ]; then
  podman unshare chcon -R "$rollback_label" \
    ~/.config/adguardhome ~/apps/docker/adguardhome
fi
podman update --restart=unless-stopped adguardhome
podman start adguardhome
```

Restore a compatible configuration backup before starting the retained
container if its settings changed during an upgrade. Reapply Ansible after
correcting the source to migrate back to Quadlet. Retained-container deletion
is a separate cleanup decision; data directories must be preserved.
