#!/usr/bin/env bash
# Adds a virtual webcam ("Phone Camera", /dev/video10) that `phone-cam` feeds with the phone's camera
# through scrcpy. Uses v4l2loopback from RPM Fusion, rebuilt by akmods for each new kernel. Run with sudo.
set -euo pipefail

echo "==> 1/3 Installing v4l2loopback (builds the module, takes a few minutes)"
dnf -y install akmod-v4l2loopback v4l2loopback
# Installing the akmod can pull in a newer kernel; build for every installed kernel that has headers.
for k in $(rpm -q --qf '%{VERSION}-%{RELEASE}.%{ARCH}\n' kernel-devel); do akmods --force --kernels "$k"; done

echo "==> 2/3 Loading it on every boot as \"Phone Camera\""
echo 'options v4l2loopback devices=1 video_nr=10 card_label="Phone Camera" exclusive_caps=1' > /etc/modprobe.d/phone-camera.conf
echo v4l2loopback > /etc/modules-load.d/phone-camera.conf

echo "==> 3/3 Loading it now"
if modinfo v4l2loopback >/dev/null 2>&1; then
  modprobe -r v4l2loopback 2>/dev/null || true
  modprobe v4l2loopback
  cat /sys/class/video4linux/video10/name
else
  echo "No module for the running kernel $(uname -r); reboot into the newest kernel and it loads automatically."
fi
echo "Done. Tell Claude."
