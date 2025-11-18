#!/usr/bin/env bash
set -euo pipefail

# prepare_ebs.sh: Format and mount an attached EBS volume device to /data
# Usage: sudo ./prepare_ebs.sh /dev/xvdf

if [ "$#" -ne 1 ]; then
  echo "Usage: sudo $0 /dev/xvdf"
  exit 1
fi

DEVICE=$1
MNT=/data

echo "Formatting $DEVICE as ext4 (if not already formatted)."
sudo mkfs -t ext4 "$DEVICE" || true
sudo mkdir -p "$MNT"
sudo mount "$DEVICE" "$MNT"
sudo chown -R $SUDO_USER:$SUDO_USER "$MNT"
echo "Mounted $DEVICE to $MNT"

echo "To make mount persistent, add a line to /etc/fstab using the device UUID:" \
     "sudo blkid $DEVICE" \
     "and add: UUID=<uuid> /data ext4 defaults,nofail 0 2"
