#!/bin/bash

# Ensure script is run with sudo
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (use sudo)"
  exit
fi

# Variables
REAL_USER=${SUDO_USER:-$USER}
CURRENT_DIR=$(pwd)
REBOOT_REQUIRED=false

echo "[+] Updating and installing dependencies..."
apt update && apt install -y dnsmasq git ffmpeg python3-picamera2 libcamera-apps-lite --no-install-recommends

# 1. USB GADGET MODE
echo "[+] Enabling USB Gadget Mode..."
if ! lsmod | grep -q "g_ether"; then
    sudo rpi-usb-gadget on
    echo "✔ USB Gadget Mode enabled."
    REBOOT_REQUIRED=true
else
    echo "✔ USB Gadget Mode already active."
fi

# 2. CAMERA DETECTION & CONFIG
echo "[+] Checking for IMX708 Camera..."
if libcamera-hello --list-cameras | grep -q "imx708"; then
    echo "✔ Camera already detected."
else
    echo "[!] Configuring IMX708 in /boot/firmware/config.txt..."
    cp /boot/firmware/config.txt /boot/firmware/config.txt.backup
    
    # Disable auto-detect and add overlay
    sed -i 's/^camera_auto_detect=1/camera_auto_detect=0/' /boot/firmware/config.txt
    [[ ! $(grep -q "camera_auto_detect=0" /boot/firmware/config.txt) ]] && echo "camera_auto_detect=0" >> /boot/firmware/config.txt
    
    if ! grep -q "dtoverlay=imx708,cam0" /boot/firmware/config.txt; then
        echo "dtoverlay=imx708,cam0" >> /boot/firmware/config.txt
    fi
    REBOOT_REQUIRED=true
fi

# 3. NETWORK: Configure Hotspot
echo "[+] Cleaning up old ReplayCam connections..."
OLD_UUID=$(nmcli -g UUID,NAME con show | grep ReplayCam | cut -d: -f1)
[ -n "$OLD_UUID" ] && nmcli con delete "$OLD_UUID"

echo "[+] Creating Hotspot on wlan0..."
nmcli con add type wifi ifname wlan0 con-name ReplayCam autoconnect yes ssid ReplayCam mode ap
nmcli con modify ReplayCam 802-11-wireless.band bg ipv4.method manual ipv4.addresses 192.168.4.1/24
nmcli con modify ReplayCam wifi-sec.key-mgmt wpa-psk wifi-sec.psk ReplayCampass1!

# 4. DNS/DHCP: dnsmasq
# Note: We bind to both wlan0 (Hotspot) and usb0 (Gadget) for maximum flexibility
echo "[+] Configuring dnsmasq..."
[ -f /etc/dnsmasq.conf ] && mv /etc/dnsmasq.conf /etc/dnsmasq.conf.bak
cat <<EOF > /etc/dnsmasq.conf
interface=wlan0
bind-dynamic
domain-needed
bogus-priv
dhcp-range=192.168.4.10,192.168.4.250,12h
address=/#/192.168.4.1
EOF

# 5. SYSTEMD SERVICES
echo "[+] Setting up Systemd Services..."
# (Same create_service logic as before, ensuring update-script runs before others)

# 6. FINALIZE
systemctl daemon-reload
systemctl enable dnsmasq update-script captive-portal loop-record

if [ "$REBOOT_REQUIRED" = true ]; then
    echo "-----------------------------------------------"
    echo "✔ Hardware changes detected. Rebooting in 3s..."
    echo "-----------------------------------------------"
    sleep 3
    reboot
else
    echo "✔ Setup complete. No reboot needed."
fi