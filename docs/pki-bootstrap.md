# PKI Bootstrap

The homelab PKI has two tiers:

```text
Homelab Root CA
└── Homelab Kubernetes Intermediate CA
    └── Kubernetes leaf certificates
```

The root private key is stored in `pass`. Kubernetes receives only the
intermediate key through a SOPS-encrypted Secret.

## Repository Files

The following public files are tracked:

```text
pki/homelab-root-ca.crt
pki/homelab-kubernetes-intermediate.crt
pki/intermediate-ca.cnf
```

Private keys, CSRs, and OpenSSL serial files under `pki/` are ignored by Git.

## Root CA

Create a passphrase in `homelab/pki/root-ca-passphrase`, restrict newly created
files, and generate an encrypted P-256 key:

```sh
umask 077

openssl ecparam -name prime256v1 -genkey -noout |
  openssl ec \
    -aes-256-cbc \
    -passout file:<(pass show homelab/pki/root-ca-passphrase) \
    -out pki/homelab-root-ca.key
```

Create a ten-year self-signed root that permits one intermediate CA level:

```sh
openssl req \
  -x509 \
  -new \
  -key pki/homelab-root-ca.key \
  -passin file:<(pass show homelab/pki/root-ca-passphrase) \
  -sha256 \
  -days 3650 \
  -subj "/O=Homelab/CN=Homelab Root CA" \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:1" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -addext "subjectKeyIdentifier=hash" \
  -out pki/homelab-root-ca.crt
```

Back up the encrypted root key and remove its working copy:

```sh
pass insert -m homelab/pki/root-ca-key < pki/homelab-root-ca.key
rm pki/homelab-root-ca.key
```

Verify the root certificate:

```sh
openssl verify \
  -CAfile pki/homelab-root-ca.crt \
  pki/homelab-root-ca.crt

openssl x509 \
  -in pki/homelab-root-ca.crt \
  -noout \
  -subject \
  -issuer \
  -dates \
  -ext basicConstraints

openssl x509 \
  -in pki/homelab-root-ca.crt \
  -noout \
  -ext keyUsage
```

## Kubernetes Intermediate CA

The committed `pki/intermediate-ca.cnf` policy requires `CA:TRUE`, limits the
intermediate to issuing leaf certificates, and restricts its key usage to
certificate and CRL signing.

Generate an unencrypted P-256 key and CSR. The key remains plaintext only until
it has been backed up and placed in a SOPS-encrypted Kubernetes Secret:

```sh
umask 077

openssl ecparam \
  -name prime256v1 \
  -genkey \
  -noout \
  -out pki/homelab-kubernetes-intermediate.key

openssl req \
  -new \
  -key pki/homelab-kubernetes-intermediate.key \
  -out pki/homelab-kubernetes-intermediate.csr \
  -subj "/O=Homelab/CN=Homelab Kubernetes Intermediate CA"
```

Verify the CSR before signing it:

```sh
openssl req \
  -in pki/homelab-kubernetes-intermediate.csr \
  -noout \
  -subject \
  -verify
```

Sign a three-year intermediate using the root key directly from `pass`:

```sh
openssl x509 \
  -req \
  -in pki/homelab-kubernetes-intermediate.csr \
  -CA pki/homelab-root-ca.crt \
  -CAkey <(pass show homelab/pki/root-ca-key) \
  -passin file:<(pass show homelab/pki/root-ca-passphrase) \
  -set_serial "0x$(openssl rand -hex 20)" \
  -days 1095 \
  -sha256 \
  -extfile pki/intermediate-ca.cnf \
  -extensions intermediate_ca \
  -out pki/homelab-kubernetes-intermediate.crt
```

Verify the chain and CA constraints:

```sh
openssl verify \
  -CAfile pki/homelab-root-ca.crt \
  pki/homelab-kubernetes-intermediate.crt

openssl x509 \
  -in pki/homelab-kubernetes-intermediate.crt \
  -noout \
  -subject \
  -issuer \
  -dates \
  -serial \
  -ext basicConstraints

openssl x509 \
  -in pki/homelab-kubernetes-intermediate.crt \
  -noout \
  -ext keyUsage
```

Verify that the certificate and key match:

```sh
diff \
  <(openssl pkey \
      -in pki/homelab-kubernetes-intermediate.key \
      -pubout) \
  <(openssl x509 \
      -in pki/homelab-kubernetes-intermediate.crt \
      -pubkey \
      -noout)
```

Back up the intermediate key in `pass`:

```sh
pass insert -m homelab/pki/kubernetes-intermediate-key \
  < pki/homelab-kubernetes-intermediate.key
```

Do not remove the working key until the SOPS-encrypted Kubernetes Secret has
been created, decrypted, and verified against the intermediate certificate.
