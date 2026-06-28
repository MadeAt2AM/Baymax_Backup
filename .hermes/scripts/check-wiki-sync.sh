#!/bin/bash
SERVICE="hermes-wiki-sync.service"
LOG="/root/Obsidian-Vaults/.sync.log"

if ! systemctl is-active --quiet "$SERVICE"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH: $SERVICE was down, restarting..." >> "$LOG"
    systemctl restart "$SERVICE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH: $SERVICE restarted" >> "$LOG"
fi