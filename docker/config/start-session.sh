#!/bin/bash
# Start or attach to a persistent tmux session
# This ensures the terminal state survives page refreshes

SESSION_NAME="vibe"

# Check if tmux session exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    # Attach to existing session
    exec tmux attach-session -t "$SESSION_NAME"
else
    # Create new session
    exec tmux new-session -s "$SESSION_NAME"
fi
