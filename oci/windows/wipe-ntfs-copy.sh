#!/usr/bin/env bash
set -euo pipefail
# Only an offline extracted NTFS partition copy, never a live device/source VM.
# Guest cipher /w clears free clusters; this also clears deleted resident files
# in unused MFT records and stale directory/journal/slack data before capture.
[[ $# == 1 && -f $1 && ! -b $1 && ! -L $1 ]] || { echo 'Usage: wipe-ntfs-copy.sh offline-partition-copy.ntfs' >&2; exit 2; }
ntfsinfo -m "$1" >/dev/null
ntfswipe --mft --directory --logfile --pagefile --tails "$1"
ntfsinfo -m "$1" >/dev/null
