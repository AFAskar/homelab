#!/usr/bin/env bash

set -euo pipefail

connection="${PODMAN_CONNECTION:-pos}"
uri=""
identity=""

while IFS=$'\t' read -r name candidate_uri candidate_identity; do
    if [[ "$name" == "$connection" ]]; then
        uri="$candidate_uri"
        identity="$candidate_identity"
        break
    fi
done < <(podman system connection list --format '{{.Name}}\t{{.URI}}\t{{.Identity}}')

if [[ -z "$uri" ]]; then
    printf 'Podman connection %q was not found.\n' "$connection" >&2
    exit 1
fi

export CONTAINER_HOST="$uri"
if [[ -n "$identity" ]]; then
    export CONTAINER_SSHKEY="$identity"
fi

exec podman-compose --in-pod=false "$@"
