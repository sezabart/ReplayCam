#!/bin/bash

# 1. CLEANUP: Remove conflicting legacy packages
echo "[-] Removing conflicting packages (dhcpcd5)..."
sudo systemctl stop dhcpcd 2>/dev/null
sudo apt remove -y dhcpcd5

# 2. INSTALL: Required tools
echo "[+] Installing hostapd, dnsmasq and python3"
sudo apt update
sudo apt install -y dnsmasq python3-pip


# 3. SETUP: camera
echo "[+] Configuring camera in /boot/firmware/config.txt"
# Backup the config file first
sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.backup

# Set camera_auto_detect=0 and add dtoverlay line
if grep -q "camera_auto_detect" /boot/firmware/config.txt; then
    sudo sed -i 's/camera_auto_detect=1/camera_auto_detect=0/' /boot/firmware/config.txt
else
    echo "camera_auto_detect=0" | sudo tee -a /boot/firmware/config.txt
fi

# Add dtoverlay line under [all] section or create it if missing
if grep -q "\[all\]" /boot/firmware/config.txt; then
    sudo sed -i '/\[all\]/a dtoverlay=imx708,cam0' /boot/firmware/config.txt
else
    echo -e "[all]\ndtoverlay=imx708,cam0" | sudo tee -a /boot/firmware/config.txt
fi


# 3. NETWORK: Configure hotspot using NetworkManager (Native to Pi 5)
echo "[+] Configuring NetworkManager Hotspot..."
# Delete old connection if exists
sudo nmcli con delete ReplayCam 2>/dev/null
# Create new AP connection
sudo nmcli con add type wifi ifname wlan0 con-name ReplayCam autoconnect yes ssid ReplayCam
# Set static IP (Manual mode) so we can run our own DHCP/DNS
sudo nmcli con modify ReplayCam 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method manual ipv4.addresses 192.168.4.1/24
sudo nmcli con modify ReplayCam wifi-sec.key-mgmt wpa-psk wifi-sec.psk ReplayCampass1!

# 4. DNS/DHCP: Configure dnsmasq for Captive Portal
echo "[+] Configuring dnsmasq..."
# Backup original
[ -f /etc/dnsmasq.conf ] && sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.bak

# Create new config
sudo tee /etc/dnsmasq.conf >/dev/null <<EOF
interface=wlan0
bind-interfaces
server=8.8.8.8
domain-needed
bogus-priv
dhcp-range=192.168.4.10,192.168.4.250,12h
# CAPTIVE PORTAL MAGIC: Resolve ALL domains to the Pi
address=/#/192.168.4.1
EOF

# 5. SERVICE: Create a systemd service for the Python Portal and loop recorder

# Create a service that runs on boot and checks for Ethernet connectivity & updates
echo "[+] Creating Ethernet-based update and clone service..."
CURRENT_DIR=$(pwd)
sudo tee /etc/systemd/system/eth-update-clone.service >/dev/null <<EOF
[Unit]
Description=Update and Clone ReplayCam on Ethernet Connection
After=network.target

[Service]
Type=simple
User=$SUDO_USER
ExecStart=$CURRENT_DIR/eth-update-clone.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo chmod +x $CURRENT_DIR/eth-update-clone.sh

echo "[+] Creating Portal System Service..."
CURRENT_DIR=$(pwd)
sudo tee /etc/systemd/system/captive-portal.service >/dev/null <<EOF
[Unit]
Description=Captive Portal Video Server
After=eth-update-clone.service dnsmasq.service

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/bin/python3 $CURRENT_DIR/portal.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "[+] Creating Loop Record System Service..."
CURRENT_DIR=$(pwd)
sudo tee /etc/systemd/system/loop-record.service >/dev/null <<EOF
[Unit]
Description=Loop Recorder
After=captive-portal.service

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/bin/python3 $CURRENT_DIR/loop_record.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF




# 6. FINALIZE
echo "[+] Enabling services..."
sudo systemctl unmask hostapd 2>/dev/null # Just in case
sudo systemctl disable hostapd # NM handles the AP, we don't need the service
sudo systemctl enable dnsmasq
sudo systemctl restart dnsmasq
sudo systemctl enable eth-update-clone
sudo systemctl restart eth-update-clone
sudo systemctl enable captive-portal
sudo systemctl restart captive-portal
sudo systemctl enable loop-record
sudo systemctl restart loop-record

echo "-----------------------------------------------"
echo "✔ Setup Complete. Rebooting in 3 seconds..."
echo "-----------------------------------------------"
sleep 3
sudo reboot