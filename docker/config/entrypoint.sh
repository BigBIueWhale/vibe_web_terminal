#!/bin/bash
# Container entrypoint: one-time setup, then start ttyd

# Configure Vibe CLI model based on VIBE_MODE env var (default: local)
if [ "$VIBE_MODE" = "cloud" ]; then
    sed -i 's/__VIBE_ACTIVE_MODEL__/devstral-cloud/' ~/.vibe/config.toml
else
    sed -i 's/__VIBE_ACTIVE_MODEL__/devstral-local/' ~/.vibe/config.toml
fi

# Start ttyd with persistent tmux session
# -W: Writable (allow client input)
# -p 7681: Port
# -t fontSize=14: Font size
# -t scrollback=10000: 10k line scrollback
# -t cursorStyle=bar: Bar cursor
# -t cursorBlink=true: Blinking cursor
# Uses start-session.sh to maintain tmux session across page refreshes
exec /usr/local/bin/ttyd -W -p 7681 \
    -t fontSize=14 \
    -t scrollback=10000 \
    -t cursorStyle=bar \
    -t cursorBlink=true \
    /home/vibe/.local/bin/start-session.sh
