#!/usr/bin/env bash
set -euo pipefail
# Local-only conversion; does not authorize a billable import or establish OCI
# compatibility. qemu-img locking rejects an in-use source; use an offline clone.
# Never change the source guest's TPM/Secure Boot checks or disk contents.
[[ $# == 2 ]] || { echo 'Usage: prepare-image.sh generalized-installed-disk output.qcow2' >&2; exit 2; }
[[ -f $1 && ! -e $2 ]] || { echo 'Source must exist; destination must not exist.' >&2; exit 2; }
umask 077
qemu-img info "$1"
qemu-img convert -p -O qcow2 "$1" "$2"
qemu-img check "$2"
echo 'Local conversion complete. OCI compatibility, sanitization, drivers and generalization still need verification before import.'
