#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VM_NAME="f1tenth-ubuntu22"
CONFIG="$(mktemp)"
trap 'rm -f "$CONFIG"' EXIT

cat >"$CONFIG" <<EOF
images:
  - location: "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-arm64.img"
    arch: "aarch64"
cpus: 4
memory: "6GiB"
disk: "30GiB"
mounts:
  - location: "$REPO_ROOT"
    mountPoint: "/mnt/F1TENTH"
    writable: false
EOF

if ! limactl list --format '{{.Name}}' | grep -qx "$VM_NAME"; then
  limactl start --name="$VM_NAME" --tty=false "$CONFIG"
else
  limactl start "$VM_NAME" >/dev/null
fi

limactl shell --workdir=/tmp "$VM_NAME" bash /mnt/F1TENTH/scripts/setup_ros2_ubuntu_humble.sh
limactl shell --workdir=/tmp "$VM_NAME" bash -lc '
  rm -rf "$HOME/F1TENTH"
  cp -a /mnt/F1TENTH "$HOME/F1TENTH"
  cd "$HOME/F1TENTH"
  bash scripts/verify_ros2_ubuntu_humble.sh
'
