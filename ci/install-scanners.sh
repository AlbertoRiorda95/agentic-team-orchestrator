#!/usr/bin/env bash
# ci/install-scanners.sh: installs syft, grype and trivy at the versions in
# ci/scanners.env, from the official GitHub releases, verifying the checksums.
# Linux amd64. CUSTOMIZE: the asset names for arm64 runners.
set -euo pipefail
source "$(dirname "$0")/scanners.env"

BIN=${SCANNERS_BIN:-$HOME/.local/bin}
mkdir -p "$BIN"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

fetch() {  # name base-url asset checksums-file
  local name=$1 base=$2 asset=$3 sums=$4
  curl -sSfL -o "$TMP/$asset" "$base/$asset"
  curl -sSfL -o "$TMP/$sums" "$base/$sums"
  (cd "$TMP" && grep " ${asset}\$" "$sums" | sha256sum -c -)
  tar -xzf "$TMP/$asset" -C "$TMP" "$name"
  install -m 0755 "$TMP/$name" "$BIN/$name"
}

fetch syft  "https://github.com/anchore/syft/releases/download/v${SYFT_VERSION}" \
  "syft_${SYFT_VERSION}_linux_amd64.tar.gz" "syft_${SYFT_VERSION}_checksums.txt"
fetch grype "https://github.com/anchore/grype/releases/download/v${GRYPE_VERSION}" \
  "grype_${GRYPE_VERSION}_linux_amd64.tar.gz" "grype_${GRYPE_VERSION}_checksums.txt"
fetch trivy "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}" \
  "trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" "trivy_${TRIVY_VERSION}_checksums.txt"

# GitHub Actions: make the tools available to the next steps
if [ -n "${GITHUB_PATH:-}" ]; then echo "$BIN" >> "$GITHUB_PATH"; fi
"$BIN/syft" version | head -2; "$BIN/grype" version | head -2; "$BIN/trivy" --version | head -1
