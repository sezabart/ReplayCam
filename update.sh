#!/bin/bash

# Define variables for easy maintenance
REPO_PATH="/home/$(whoami)/ReplayCam"
LOG_FILE="/var/log/update_script.log"

# Function to check connectivity
check_internet() {
    # Check if either eth0 or usb0 is up AND we can ping Google
    if [[ $(cat /sys/class/net/eth0/operstate 2>/dev/null) == "up" ]] || \
       [[ $(cat /sys/class/net/usb0/operstate 2>/dev/null) == "up" ]]; then
        ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1
        return $?
    fi
    return 1
}

# Wait for connection (up to 60 seconds)
MAX_RETRIES=12
COUNT=0
while ! check_internet; do
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo "No internet connection detected. Exiting." >> "$LOG_FILE"
        exit 1
    fi
    sleep 5
    ((COUNT++))
done

# Perform apt update and upgrade
apt-get update && apt-get upgrade -y
# Update the repo
git pull origin main