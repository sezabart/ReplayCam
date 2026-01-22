#!/bin/bash

# Wait until Ethernet is connected (e.g., eth0 or usb0)
if ip link show eth0 | grep -q 'state UP'; then
    # Perform apt update and upgrade
    sudo apt update && sudo apt upgrade -y

    cd ~/ReplayCam
    git pull origin main
    

    # Optionally, install Python dependencies if requirements.txt exists
    if [ -f "~/ReplayCam/requirements.txt" ]; then
        sudo pip3 install -r ~/ReplayCam/requirements.txt
    fi
fi