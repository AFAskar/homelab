# Homelab

this is hold my current homelab state since i use argocd for gitOps if you want to run the exact same services as me you are more than welcome to fork this repository and augment it for your needs

# Future Goals:

- [ ] ExternalDNS integration for auto provisioned records instead of the current traefik with wildcard
- [ ] cert-manager integration for automated TLS certificate provisioning and renewal
- [ ] argocd without port forwarding

# Cluster Rebuild Instructions

## SOPS secret

```sh
pass show homelab/sops/age-key |
  kubectl -n argocd create secret generic sops-age \
    --from-file=keys.txt=/dev/stdin
```
