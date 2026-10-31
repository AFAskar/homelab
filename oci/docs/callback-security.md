# Panel callback isolation

Wings uses Thor's private HTTPS proxy because paid nodes have no Tailscale agent.
The proxy connects to **pos's tailnet IP, port 8443**, using the existing CA and
Panel hostname/SNI. It never disables certificate verification.

| Source | Destination | Permission |
|---|---|---|
| Wings subnet | Thor private :443 | Existing Panel callback proxy |
| Thor tailnet identity | pos tailnet :8443 | Panel `/api/remote/…` only |
| Thor | pos :443, :80, :32443; optiplex :8443 | Denied by Tailscale |
| Other remote sources / LAN | Callback :8443 and NodePort :32443 | Dropped by host firewall |
| Administrator | Normal Panel HTTPS :443 | Existing access preserved |

Traefik's `pelican-callback` entrypoint listens inside its pod on 9443,
exposed through ServiceLB 8443 / NodePort 32443. Only `web` and `websecure`
are default entrypoints: ordinary Ingress resources cannot implicitly appear
on the callback listener. The sole callback IngressRoute matches the exact
Panel hostname and `/api/remote/` path boundary; other hosts, UI, client API
and application API paths have no route. No prefix stripping is used.
Pelican's installed rc.2 daemon middleware still validates each node token.
This restricts service reachability; it does not make a stolen node token safe.

`oci/ansible/callback-firewall.yaml` installs persistent filtering on **both**
k3s hosts. The IPv4 raw PREROUTING chain admits only Thor's Tailscale source
on `tailscale0`; everything else to the two local callback ports is dropped.
Filtering before kube-proxy/ServiceLB DNAT avoids an INPUT-only bypass.
IPv6 callback ingress is denied. Services start before k3s on systemd/OpenRC.
The normal HTTPS listener and administrator SSH are unaffected.

## Rollout and recovery

1. Validate/render the installed Traefik chart and server-dry-run the manifests.
2. Run `ansible-playbook callback-firewall.yaml` from `oci/ansible/`.
3. Sync the reviewed Traefik HelmChartConfig and Panel callback IngressRoute.
   During PR staging, pin live Argo Applications to the reviewed commit;
   do not merge or let the old main revision undo the listener change.
4. Temporarily allow Thor both 443 and 8443 through a reviewed targeted
   Tailscale-only Terraform plan. For both `thor` and `tag:oci-router` embedded
   tests, move `pos:443` from `deny` to `accept` in that temporary policy; keep
   `pos:8443` accepted. Tests must match the policy being planned. Test the new
   route before switching Caddy.
5. Run `ansible-playbook tailscale/panel-proxy.yaml` to switch the upstream.
6. Restore the final grant and tests: remove 443 permission, move `pos:443`
   back to `deny`, and keep `pos:8443` accepted. Plan and apply that final
   policy; discard all earlier policy plans.
7. Verify authenticated Wings callbacks, normal Panel UI and public games.
   From Thor, require callback requests without credentials to return 401,
   other hosts/paths to return 404, and pos:443 to be unreachable. From the
   administrator's LAN, require callback 8443 and NodePort 32443 to be blocked.

If callbacks fail, inspect Traefik routing, CA/SNI, Caddy and daemon-token
errors. Recover the dedicated endpoint using existing administrator SSH.
Do not casually restore shared 443 access or apply an old saved policy plan.
No new OCI instance, paid service, CA or client certificate is required.

## Check access

From Thor, request `https://pelican.home.internal:8443/api/remote/servers`
against pos's tailnet IP with verified Panel SNI/CA. Override the OCI guest's
normal DNS mapping to Thor for this direct listener check:

```bash
curl --resolve pelican.home.internal:8443:100.114.113.82 \
  --cacert /usr/local/share/ca-certificates/homelab-root-ca.crt \
  --silent --output /dev/null --write-out '%{http_code}\n' \
  https://pelican.home.internal:8443/api/remote/servers
```

Require 401 without a
node token and 200 with the appropriate token. Do not put a node token in a
shell command, process argument or committed report. Supply it through a
private stdin/request mechanism.

Check that `/`, `/admin`, `/api/client`, `/api/application` and another
hostname return 404 on this listener. Fresh connections from Thor to pos:443,
pos:80 and the alternate NodePort must fail. Test callback/NodePort blocking
from the LAN too. Repeat authenticated callbacks from each Wings node and
check the normal Panel UI and game probes after a change.

## Stage an unmerged change

If deploying a reviewed unmerged change, configure the parent `homelab` Argo
Application to ignore only the
`traefik-config` Application's `/spec/source/targetRevision`, with
`RespectIgnoreDifferences=true`, so its self-heal cannot reset the reviewed
PR revision to old main. Other applications continue their normal sync.
After an approved merge, set the child revision to main, then remove that
specific ignoreDifferences entry (and the respect option if no other rule
needs it). Save the previous parent spec privately for comparison.
Do not remove this staging exception before main contains the listener.
