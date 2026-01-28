#!/bin/bash
# =============================================================================
# cleanup-sessions.sh — Remove all Vibe Terminal session containers and data
# =============================================================================
#
# This script ONLY removes resources that belong to this application:
#   - Docker containers named "vibe-session-*"
#   - Workspace directories under data/workspaces/ and /tmp/vibe-workspaces/
#   - Session ownership records in data/session_owners.json
#
# It does NOT touch:
#   - The "vibe-terminal:latest" Docker image (use docker rmi to remove)
#   - Any other Docker containers, images, volumes, or networks
#   - auth.yaml, SSL certs, or any other configuration
#
# Usage:
#   ./cleanup-sessions.sh          # interactive: shows what will be deleted
#   ./cleanup-sessions.sh --force  # no prompts, just delete everything
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_PREFIX="vibe-session-"
DATA_DIR="$SCRIPT_DIR/data"
OLD_WORKSPACE_DIR="/tmp/vibe-workspaces"

FORCE=false
if [[ "${1:-}" == "--force" || "${1:-}" == "-f" ]]; then
    FORCE=true
fi

# --- Discover what exists ---------------------------------------------------

echo "Scanning for Vibe Terminal session resources..."
echo ""

# Find containers (running + stopped)
CONTAINERS=$(docker ps -a --filter "name=$CONTAINER_PREFIX" --format "{{.ID}}\t{{.Names}}\t{{.Status}}" 2>/dev/null || true)
if [[ -z "$CONTAINERS" ]]; then
    CONTAINER_COUNT=0
else
    CONTAINER_COUNT=$(echo "$CONTAINERS" | wc -l)
fi

# Find workspace directories
WORKSPACE_DIRS=()
if [[ -d "$DATA_DIR/workspaces" ]]; then
    while IFS= read -r -d '' dir; do
        WORKSPACE_DIRS+=("$dir")
    done < <(find "$DATA_DIR/workspaces" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)
fi

OLD_WORKSPACE_DIRS=()
if [[ -d "$OLD_WORKSPACE_DIR" ]]; then
    while IFS= read -r -d '' dir; do
        OLD_WORKSPACE_DIRS+=("$dir")
    done < <(find "$OLD_WORKSPACE_DIR" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)
fi

# Check owner store
OWNER_FILE="$DATA_DIR/session_owners.json"
OWNER_EXISTS=false
OWNER_COUNT=0
if [[ -f "$OWNER_FILE" ]]; then
    OWNER_EXISTS=true
    # Count entries (number of keys in top-level JSON object)
    OWNER_COUNT=$(python3 -c "import json; print(len(json.load(open('$OWNER_FILE'))))" 2>/dev/null || echo 0)
fi

# --- Show summary -----------------------------------------------------------

echo "Found:"
echo "  Containers:       $CONTAINER_COUNT"
echo "  Workspaces (new): ${#WORKSPACE_DIRS[@]}"
echo "  Workspaces (old): ${#OLD_WORKSPACE_DIRS[@]}"
echo "  Owner records:    $OWNER_COUNT"
echo ""

if [[ "$CONTAINER_COUNT" -eq 0 && ${#WORKSPACE_DIRS[@]} -eq 0 && ${#OLD_WORKSPACE_DIRS[@]} -eq 0 && "$OWNER_COUNT" -eq 0 ]]; then
    echo "Nothing to clean up."
    exit 0
fi

# List containers
if [[ "$CONTAINER_COUNT" -gt 0 ]]; then
    echo "Containers to remove:"
    echo "$CONTAINERS" | while IFS=$'\t' read -r id name status; do
        echo "  - $name ($status)"
    done
    echo ""
fi

# List workspaces
if [[ ${#WORKSPACE_DIRS[@]} -gt 0 ]]; then
    echo "Workspace directories to remove (data/workspaces/):"
    for dir in "${WORKSPACE_DIRS[@]}"; do
        size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        echo "  - $(basename "$dir")  ($size)"
    done
    echo ""
fi

if [[ ${#OLD_WORKSPACE_DIRS[@]} -gt 0 ]]; then
    echo "Old workspace directories to remove (/tmp/vibe-workspaces/):"
    for dir in "${OLD_WORKSPACE_DIRS[@]}"; do
        size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        echo "  - $(basename "$dir")  ($size)"
    done
    echo ""
fi

# --- Confirm -----------------------------------------------------------------

if [[ "$FORCE" != true ]]; then
    read -p "Delete all of the above? [y/N] " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Aborted."
        exit 0
    fi
    echo ""
fi

# --- Delete ------------------------------------------------------------------

# 1. Stop and remove containers
if [[ "$CONTAINER_COUNT" -gt 0 ]]; then
    echo "Stopping and removing containers..."
    echo "$CONTAINERS" | while IFS=$'\t' read -r id name status; do
        echo "  Removing $name..."
        docker rm -f "$id" >/dev/null 2>&1 || true
    done
    echo "  Done."
    echo ""
fi

# 2. Remove workspace directories (new location)
#    Files inside were created by Docker containers (different UID), so plain
#    rm may fail with "Permission denied". We use a throwaway Docker container
#    running as root to delete everything cleanly.
if [[ ${#WORKSPACE_DIRS[@]} -gt 0 ]]; then
    echo "Removing workspace directories (data/workspaces/)..."
    docker run --rm -v "$DATA_DIR/workspaces:/cleanup" alpine sh -c "rm -rf /cleanup/*" 2>/dev/null \
        || rm -rf "$DATA_DIR/workspaces"/* 2>/dev/null || true
    echo "  Done."
    echo ""
fi

# 3. Remove old workspace directories
if [[ ${#OLD_WORKSPACE_DIRS[@]} -gt 0 ]]; then
    echo "Removing old workspace directories (/tmp/vibe-workspaces/)..."
    docker run --rm -v "$OLD_WORKSPACE_DIR:/cleanup" alpine sh -c "rm -rf /cleanup/*" 2>/dev/null \
        || rm -rf "$OLD_WORKSPACE_DIR"/* 2>/dev/null || true
    echo "  Done."
    echo ""
fi

# 4. Clear owner store
if [[ "$OWNER_EXISTS" == true ]]; then
    echo "Clearing session ownership records..."
    echo "{}" > "$OWNER_FILE"
    echo "  Cleared $OWNER_COUNT record(s) from $OWNER_FILE"
    echo ""
fi

# --- Verify ------------------------------------------------------------------

remaining=$(docker ps -a --filter "name=$CONTAINER_PREFIX" --format "{{.ID}}" 2>/dev/null | wc -l)
echo "Cleanup complete."
echo "  Remaining vibe-session containers: $remaining"
echo ""
echo "The vibe-terminal:latest Docker image is still available for rebuilding."
echo "To rebuild: docker build -t vibe-terminal:latest docker/"
