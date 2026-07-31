#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

sudo install \
  -o root \
  -g root \
  -m 0755 \
  "$PROJECT_DIR/helper/appsweep-helper" \
  /usr/libexec/appsweep-helper

sudo install \
  -o root \
  -g root \
  -m 0644 \
  "$PROJECT_DIR/data/tech.shoaib.AppSweep.policy" \
  /usr/share/polkit-1/actions/tech.shoaib.AppSweep.policy

echo "Privileged helper installed."
