# Cluster Rebuild

## SOPS Bootstrap

Argo CD needs the age identity before KSOPS can decrypt secrets from Git. Restore
the bootstrap secret after installing Argo CD and before synchronizing
applications containing encrypted secrets:

```sh
pass show homelab/sops/age-key |
  kubectl -n argocd create secret generic sops-age \
    --from-file=keys.txt=/dev/stdin
```

Confirm that the restored identity has the recipient configured in
`.sops.yaml` without printing the private identity:

```sh
kubectl -n argocd get secret sops-age \
  -o jsonpath='{.data.keys\.txt}' |
  base64 -d |
  age-keygen -y
```

Argo CD creates the SOPS-encrypted intermediate CA Secret during its normal
synchronization. The root private key is not required for a routine cluster
rebuild.

## Password Store Entries

The rebuild process expects these entries:

```text
homelab/pki/root-ca-key
homelab/pki/root-ca-passphrase
homelab/pki/kubernetes-intermediate-key
homelab/sops/age-key
```

The root and intermediate certificates are public and are tracked under
`pki/`.
