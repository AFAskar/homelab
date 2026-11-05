#!/usr/bin/env bash
set -euo pipefail
# Pinned stable VirtIO-Win 0.1.302-1 guest-tools MSI from the upstream project:
# https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/archive-virtio/virtio-win-0.1.302-1/virtio-win-gt-x64.msi
# Extract only; the MSI is not executed. Windows verifies the driver catalogs.
[[ $# == 2 && -f $1 && ! -e $2 ]] || { echo 'Usage: extract-virtio.sh downloaded.msi new-output-directory' >&2; exit 2; }
[[ $(sha256sum "$1" | cut -d' ' -f1) == 4f4388468a7ac5286bd1f1924ef02e7281a60a600390a7cfcfd55809efc0889f ]] || { echo 'Unexpected MSI checksum; review the release before upgrading.' >&2; exit 2; }
umask 077
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
7z x -y "-o$work" "$1" >/dev/null
mkdir -p "$2"
for driver in viostor vioscsi netkvm; do
  mkdir "$2/$driver"
  for extension in inf cat sys; do
    cp "$work/FILE_${driver}_w11_amd64.$extension" "$2/$driver/$driver.$extension"
  done
done
cp "$work/FILE_netkvm_netkvmp_w11_amd64" "$2/netkvm/netkvmp.exe"
