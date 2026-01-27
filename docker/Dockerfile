# Ubuntu-based terminal container with Vibe CLI
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm-256color
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Install essential packages
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    vim \
    nano \
    htop \
    tree \
    jq \
    ripgrep \
    fd-find \
    bat \
    fzf \
    tmux \
    zsh \
    sudo \
    openssh-client \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    ca-certificates \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Generate locale
RUN locale-gen en_US.UTF-8

# Install ttyd for web terminal
RUN wget -O /usr/local/bin/ttyd https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 \
    && chmod +x /usr/local/bin/ttyd

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Create user with password "password"
RUN useradd -m -s /bin/bash -G sudo vibe \
    && echo "vibe:password" | chpasswd \
    && echo "vibe ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to vibe user for installations
USER vibe
WORKDIR /home/vibe

# Install uv for vibe user
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/vibe/.local/bin:$PATH"

# Install Vibe CLI
RUN /home/vibe/.local/bin/uv tool install mistral-vibe

# Create vibe config directory
RUN mkdir -p /home/vibe/.vibe

# Copy vibe configuration (will be added at build time)
COPY --chown=vibe:vibe config/vibe-config.toml /home/vibe/.vibe/config.toml
COPY --chown=vibe:vibe config/vibe-env /home/vibe/.vibe/.env

# Create workspace directory for user files
RUN mkdir -p /home/vibe/workspace

# Create a nice bashrc
RUN echo 'export PS1="\[\033[1;32m\]\u@vibe-terminal\[\033[0m\]:\[\033[1;34m\]\w\[\033[0m\]\$ "' >> /home/vibe/.bashrc \
    && echo 'alias ll="ls -la"' >> /home/vibe/.bashrc \
    && echo 'alias la="ls -A"' >> /home/vibe/.bashrc \
    && echo 'export PATH="/home/vibe/.local/bin:$PATH"' >> /home/vibe/.bashrc \
    && echo 'cd /home/vibe/workspace' >> /home/vibe/.bashrc \
    && echo '' >> /home/vibe/.bashrc \
    && echo '# Welcome message' >> /home/vibe/.bashrc \
    && echo 'echo ""' >> /home/vibe/.bashrc \
    && echo 'echo "Welcome to Vibe Terminal!"' >> /home/vibe/.bashrc \
    && echo 'echo "- Type \"vibe\" to start Mistral Vibe CLI"' >> /home/vibe/.bashrc \
    && echo 'echo "- Your workspace is /home/vibe/workspace"' >> /home/vibe/.bashrc \
    && echo 'echo "- Password for sudo: password"' >> /home/vibe/.bashrc \
    && echo 'echo ""' >> /home/vibe/.bashrc

WORKDIR /home/vibe/workspace

# Expose ttyd port
EXPOSE 7681

# Default command: start ttyd with enhanced options
# -W: Writable (allow client input)
# -p 7681: Port
# -t fontSize=14: Font size
# -t scrollback=10000: 10k line scrollback
# -t cursorStyle=bar: Bar cursor
# -t cursorBlink=true: Blinking cursor
CMD ["/usr/local/bin/ttyd", "-W", "-p", "7681", "-t", "fontSize=14", "-t", "scrollback=10000", "-t", "cursorStyle=bar", "-t", "cursorBlink=true", "/bin/bash", "-l"]
