# Homelab

this is hold my current homelab state since i use argocd for gitOps if you want to run the exact same services as me you are more than welcome to fork this repository and augment it for your needs

## Adding Services

there is a helper script available `createapp.sh` you just pass the name of the service you want to add as an argument and it will create the folders as expected by argocd
however you still need to write the manifests yourself

# Future Goals:

- [x] cert-manager integration for automated TLS certificate provisioning and renewal
- [x] argocd without port forwarding
- [ ] ExternalDNS integration for auto provisioned records instead of the current traefik with wildcard

Cluster rebuild and PKI procedures are documented in [`docs/`](docs/).
