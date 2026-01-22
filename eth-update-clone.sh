#!/bin/bash

# Wait until Ethernet is connected (e.g., eth0 or usb0)
if ip link show eth0 | grep -q 'state UP'; do
    

    # Perform apt update and upgrade
    sudo apt update && sudo apt upgrade -y

    # Clone the repository if not already present
    if [ ! -d "/home/pi/ReplayCam" ]; then
        cd /home/pi
        git clone https://github.com/sezabart/ReplayCam.git
    else
        cd /home/pi/ReplayCam
        git pull origin main
    fi

    # Optionally, install Python dependencies if requirements.txt exists
    if [ -f "/home/pi/ReplayCam/requirements.txt" ]; then
        sudo pip3 install -r /home/pi/ReplayCam/requirements.txt
    fi
fi