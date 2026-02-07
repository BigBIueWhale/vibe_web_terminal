#!/bin/bash
# Start or attach to a persistent tmux session
# This ensures the terminal state survives page refreshes

# Fix workspace ownership (mounted from host with different UID)
sudo chown -R vibe:vibe /home/vibe/workspace 2>/dev/null

# Export secrets (e.g. MISTRAL_API_KEY) so OpenCode can read them
set -a
source ~/.vibe/.env 2>/dev/null
set +a

# Configure Vibe CLI model based on VIBE_MODE env var (default: local)
if [ "$VIBE_MODE" = "cloud" ]; then
    sed -i 's/__VIBE_ACTIVE_MODEL__/devstral-cloud/' ~/.vibe/config.toml
else
    sed -i 's/__VIBE_ACTIVE_MODEL__/devstral-local/' ~/.vibe/config.toml
fi

SESSION_NAME="vibe"

# Check if tmux session exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    # Attach to existing session
    exec tmux attach-session -t "$SESSION_NAME"
else
    # Create detached, pre-type command, then attach
    tmux new-session -d -s "$SESSION_NAME"
    sleep 0.5
    tmux send-keys -t "$SESSION_NAME" "opencode"
    exec tmux attach-session -t "$SESSION_NAME"
fi
