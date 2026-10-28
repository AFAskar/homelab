#!/usr/bin/env bash
set -euo pipefail
# Conversion only after OCI confirms a supported Windows 11 custom-image TPM path.
# Never bypass TPM, Secure Boot, or CPU requirements.
: "${OCI_WIN11_COMPATIBILITY_EVIDENCE:?Blocked: OCI shielded instances do not support custom images; supply reviewed evidence of a supported path}"
[[ -f $OCI_WIN11_COMPATIBILITY_EVIDENCE ]] || exit 2
[[ $# == 2 ]] || { echo 'Usage: prepare-image.sh generalized-installed-disk output.qcow2' >&2; exit 2; }
[[ -f $1 && ! -e $2 ]] || { echo 'Source must exist; destination must not exist.' >&2; exit 2; }
umask 077
qemu-img info "$1"
qemu-img convert -p -O qcow2 "$1" "$2"
qemu-img check "$2"
echo 'Conversion complete. Guest installation, VirtIO drivers, UEFI/TPM verification and sysprep must already be evidenced.'
