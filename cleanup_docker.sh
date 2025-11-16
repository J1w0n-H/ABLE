#!/usr/bin/env bash
set -euo pipefail

echo "[1/4] Stopping running containers..."
docker ps -q | xargs -r docker stop

echo "[2/4] Removing containers, networks, images, cache..."
docker system prune -af

echo "[3/4] Removing dangling volumes..."
docker volume prune -f

echo "[4/4] Clearing Docker tmp cache..."
sudo rm -rf /var/lib/docker/tmp/*

echo "Docker cleanup completed."
