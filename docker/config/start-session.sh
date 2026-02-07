#!/bin/bash
# Start or attach to a persistent tmux session
# This ensures the terminal state survives page refreshes

# Fix workspace ownership (mounted from host with different UID)
sudo chown -R vibe:vibe /home/vibe/workspace 2>/dev/null

# Export secrets (e.g. MISTRAL_API_KEY) so Vibe/OpenCode can read them
set -a
source ~/.vibe/.env 2>/dev/null
set +a

SESSION_NAME="vibe"

# Check if tmux session exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    # Attach to existing session
    exec tmux attach-session -t "$SESSION_NAME"
else
    # Create detached, pre-type command, then attach
    tmux new-session -d -s "$SESSION_NAME"
    sleep 0.5
    tmux send-keys -t "$SESSION_NAME" "vibe --agent auto-approve"
    exec tmux attach-session -t "$SESSION_NAME"
fi
