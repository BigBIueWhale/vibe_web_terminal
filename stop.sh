#!/bin/bash
# Stop all vibe-terminal containers and clean up

echo "Stopping all Vibe Terminal containers..."

# Stop and remove all vibe-session containers
docker ps -a --filter "name=vibe-session-" --format "{{.ID}}" | xargs -r docker rm -f

echo "Cleaning up workspaces..."
rm -rf /tmp/vibe-workspaces/*

echo "Done."
