#!/bin/bash
# Re-applies compose.yaml changes to Home Assistant, Mosquitto and ps5-mqtt.
set -euo pipefail
cd /home/shanerunham/homelab
docker compose up -d homeassistant mosquitto ps5-mqtt
docker compose ps homeassistant mosquitto ps5-mqtt
