# Ubuntu-based terminal container with Vibe CLI
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm-256color
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# ============================================================
# SYSTEM PACKAGES
# ============================================================

# Core utilities & shell tools
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    aria2 \
    vim \
    nano \
    emacs-nox \
    htop \
    tree \
    jq \
    yq \
    ripgrep \
    fd-find \
    bat \
    fzf \
    tmux \
    screen \
    zsh \
    sudo \
    openssh-client \
    openssh-server \
    ca-certificates \
    locales \
    man-db \
    less \
    file \
    unzip \
    zip \
    p7zip-full \
    xz-utils \
    bzip2 \
    rsync \
    strace \
    ltrace \
    lsof \
    sysstat \
    patch \
    diffutils \
    colordiff \
    dos2unix \
    rename \
    pv \
    parallel \
    entr \
    at \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Git & version control tools
RUN apt-get update && apt-get install -y \
    git \
    git-lfs \
    gitk \
    git-gui \
    git-svn \
    git-doc \
    tig \
    subversion \
    mercurial \
    && rm -rf /var/lib/apt/lists/*

# Network utilities & diagnostics
RUN apt-get update && apt-get install -y \
    socat \
    netcat-openbsd \
    iputils-ping \
    iputils-arping \
    iputils-tracepath \
    net-tools \
    dnsutils \
    iproute2 \
    traceroute \
    telnet \
    nmap \
    tcpdump \
    iftop \
    nethogs \
    mtr-tiny \
    whois \
    openssl \
    iperf3 \
    httpie \
    ca-certificates \
    apt-transport-https \
    gnupg2 \
    wireguard-tools \
    openvpn \
    sshpass \
    sshfs \
    && rm -rf /var/lib/apt/lists/*

# Build toolchain & compilers
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    gfortran \
    cmake \
    cmake-curses-gui \
    make \
    automake \
    autoconf \
    libtool \
    pkg-config \
    nasm \
    yasm \
    swig \
    ccache \
    ninja-build \
    meson \
    && rm -rf /var/lib/apt/lists/*

# Boost C++ libraries (commonly used subset instead of libboost-all-dev)
RUN apt-get update && apt-get install -y \
    libboost-dev \
    libboost-filesystem-dev \
    libboost-system-dev \
    libboost-thread-dev \
    libboost-program-options-dev \
    libboost-regex-dev \
    libboost-iostreams-dev \
    libboost-serialization-dev \
    libboost-date-time-dev \
    libboost-test-dev \
    libboost-log-dev \
    libboost-json-dev \
    && rm -rf /var/lib/apt/lists/*

# C/C++ debugging, analysis & sanitizer tools
# (clang/clang-format/clang-tidy only — full LLVM/lldb/lld/libc++ dropped to save ~300 MB)
RUN apt-get update && apt-get install -y \
    gdb \
    gdbserver \
    gdb-multiarch \
    valgrind \
    clang \
    clang-format \
    clang-tidy \
    cppcheck \
    iwyu \
    binutils \
    binutils-multiarch \
    elfutils \
    dwarves \
    strace \
    ltrace \
    linux-tools-common \
    && rm -rf /var/lib/apt/lists/*

# Embedded & cross-compilation tools
# (kept arm-none-eabi + aarch64; dropped armhf + riscv64 + qemu-system-misc to save ~300 MB)
RUN apt-get update && apt-get install -y \
    gcc-arm-none-eabi \
    gdb-arm-none-eabi \
    libnewlib-arm-none-eabi \
    gcc-aarch64-linux-gnu \
    g++-aarch64-linux-gnu \
    openocd \
    minicom \
    picocom \
    u-boot-tools \
    device-tree-compiler \
    qemu-user-static \
    qemu-system-arm \
    && rm -rf /var/lib/apt/lists/*

# Buildroot build dependencies (full list for Ubuntu 24.04)
RUN apt-get update && apt-get install -y \
    bc \
    cpio \
    gawk \
    findutils \
    libncurses-dev \
    libncursesw5-dev \
    texinfo \
    bison \
    flex \
    gettext \
    libelf-dev \
    libmpfr-dev \
    libmpc-dev \
    libgmp-dev \
    libisl-dev \
    dialog \
    lzop \
    squashfs-tools \
    mtd-utils \
    genext2fs \
    e2fsprogs \
    dosfstools \
    mtools \
    fakeroot \
    && rm -rf /var/lib/apt/lists/*

# Yocto Project / OpenEmbedded build dependencies (Ubuntu 24.04)
RUN apt-get update && apt-get install -y \
    gawk \
    diffstat \
    chrpath \
    socat \
    cpio \
    texinfo \
    python3-pexpect \
    python3-git \
    python3-jinja2 \
    python3-subunit \
    zstd \
    liblz4-tool \
    debianutils \
    libsdl2-dev \
    mesa-common-dev \
    libglu1-mesa-dev \
    xterm \
    iproute2 \
    gcc-multilib \
    g++-multilib \
    lib32z1-dev \
    libc6-dev-i386 \
    pylint \
    rpcsvc-proto \
    lz4 \
    xz-utils \
    locales \
    screen \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# PCAP, Wireshark & network packet analysis
# wireshark-common includes editcap, mergecap, capinfos, reordercap, text2pcap
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    libpcap-dev \
    tshark \
    wireshark-common \
    tcpdump \
    tcpreplay \
    tcpflow \
    ngrep \
    libnet1-dev \
    libnl-3-dev \
    libnl-genl-3-dev \
    libnl-route-3-dev \
    libnetfilter-queue-dev \
    libgeoip-dev \
    ethtool \
    ipset \
    conntrack \
    && rm -rf /var/lib/apt/lists/*

# Python ecosystem
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    && rm -rf /var/lib/apt/lists/*

# Node.js & JavaScript ecosystem
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Bun JavaScript/TypeScript runtime (installed globally)
RUN curl -fsSL https://bun.sh/install | BUN_INSTALL=/usr/local bash

# Headless browser dependencies (Playwright provides its own Chromium binary)
RUN apt-get update && apt-get install -y \
    xvfb \
    xauth \
    dbus \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libxrandr2 \
    libasound2t64 \
    libatk1.0-0t64 \
    libatk-bridge2.0-0t64 \
    libcups2t64 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0t64 \
    libnspr4 \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    fonts-liberation \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# HTML tidy & validation tools
RUN apt-get update && apt-get install -y \
    tidy \
    libxml2-utils \
    xmlstarlet \
    && rm -rf /var/lib/apt/lists/*

# Pre-install global npm packages (browser automation, scraping, utilities)
RUN npm install -g \
    puppeteer \
    playwright \
    cheerio \
    jsdom \
    axios \
    node-fetch \
    got \
    undici \
    turndown \
    readability-cli \
    linkedom \
    dompurify \
    sanitize-html \
    html-minifier-terser \
    clean-css-cli \
    terser \
    uglify-js \
    js-beautify \
    prettier \
    eslint \
    typescript \
    ts-node \
    tsx \
    esbuild \
    webpack-cli \
    webpack \
    vite \
    rollup \
    babel-cli \
    nodemon \
    pm2 \
    express \
    fastify \
    zod \
    lodash \
    underscore \
    ramda \
    date-fns \
    moment \
    dayjs \
    uuid \
    nanoid \
    chalk \
    commander \
    yargs \
    inquirer \
    ora \
    boxen \
    sharp \
    jimp \
    pdf-lib \
    pdfkit \
    csv-parser \
    csv-stringify \
    xlsx \
    json5 \
    yaml \
    toml \
    dotenv \
    marked \
    markdown-it \
    highlight.js \
    mermaid \
    d3 \
    puppeteer-extra \
    puppeteer-extra-plugin-stealth \
    http-server \
    live-server \
    concurrently \
    cross-env \
    rimraf \
    glob \
    minimatch \
    semver \
    debug

# More npm tools for agents: JSON/data manipulation, scaffolding, dev utils
RUN npm install -g \
    fx \
    json-diff \
    json-server \
    serve \
    localtunnel \
    degit \
    svgo \
    npm-check-updates \
    depcheck \
    madge \
    license-checker \
    tree-sitter-cli \
    wappalyzer \
    tldr \
    speed-test \
    is-up-cli \
    public-ip-cli \
    internal-ip-cli \
    fkill-cli \
    empty-trash-cli \
    clipboard-cli \
    open-cli

# Java Runtime (JRE only — JDK dropped to save ~50 MB; only needed for tabula-py)
RUN apt-get update && apt-get install -y \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Libraries: image processing, PDF, graphics, ICU (for Hebrew/Arabic/Bidi)
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    libfreetype6-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libglib2.0-dev \
    librsvg2-dev \
    libmagic1 \
    libmagickwand-dev \
    libicu-dev \
    icu-devtools \
    libfribidi-dev \
    libharfbuzz-dev \
    && rm -rf /var/lib/apt/lists/*

# Cryptography & TLS system libraries
RUN apt-get update && apt-get install -y \
    libssl-dev \
    libsodium-dev \
    libgcrypt20-dev \
    libgnutls28-dev \
    libargon2-dev \
    libnss3-dev \
    libsasl2-dev \
    libkrb5-dev \
    libscrypt-dev \
    libsecret-1-dev \
    gnutls-bin \
    p11-kit \
    softhsm2 \
    && rm -rf /var/lib/apt/lists/*

# OCR: Tesseract with language packs
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-heb \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-spa \
    libtesseract-dev \
    leptonica-progs \
    && rm -rf /var/lib/apt/lists/*

# PDF tools & document conversion
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libpoppler-dev \
    libpoppler-cpp-dev \
    ghostscript \
    qpdf \
    pandoc \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# LibreOffice (minimal: writer + calc for doc conversion, dropped impress + draw to save ~600 MB)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*

# Database clients & libraries
RUN apt-get update && apt-get install -y \
    sqlite3 \
    libsqlite3-dev \
    postgresql-client \
    libpq-dev \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Math, science & data libraries (C-level)
RUN apt-get update && apt-get install -y \
    liblapack-dev \
    libblas-dev \
    libopenblas-dev \
    libhdf5-dev \
    libgeos-dev \
    libproj-dev \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Multimedia, audio & video conversion
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libavutil-dev \
    libavfilter-dev \
    libavdevice-dev \
    imagemagick \
    sox \
    libsox-dev \
    libsox-fmt-all \
    mediainfo \
    libmediainfo-dev \
    libsndfile1-dev \
    vorbis-tools \
    lame \
    flac \
    opus-tools \
    mkvtoolnix \
    exiftool \
    webp \
    optipng \
    pngquant \
    jpegoptim \
    gifsicle \
    && rm -rf /var/lib/apt/lists/*

# Graph & visualization tools
RUN apt-get update && apt-get install -y \
    graphviz \
    libgraphviz-dev \
    gnuplot \
    && rm -rf /var/lib/apt/lists/*

# Fonts: Hebrew, Arabic, CJK, general
RUN apt-get update && apt-get install -y \
    fonts-dejavu \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    fonts-liberation \
    fonts-liberation2 \
    fonts-noto \
    fonts-noto-color-emoji \
    fonts-noto-mono \
    fonts-freefont-ttf \
    fonts-opensymbol \
    fonts-open-sans \
    fonts-roboto \
    fonts-firacode \
    fonts-hack \
    culmus \
    culmus-fancy \
    fonts-hosny-amiri \
    fonts-arabeyes \
    fonts-kacst \
    fonts-kacst-one \
    fonts-droid-fallback \
    fonts-indic \
    fonts-thai-tlwg \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Extra fonts: emoji, powerline, monospace, symbol, icon
RUN apt-get update && apt-get install -y \
    fonts-noto-extra \
    fonts-symbola \
    fonts-powerline \
    fonts-font-awesome \
    fonts-ubuntu \
    fonts-ubuntu-console \
    fonts-cascadia-code \
    fonts-jetbrains-mono \
    fonts-lato \
    fonts-material-design-icons-iconfont \
    fonts-emojione \
    fonts-ancient-scripts \
    fonts-wine \
    xfonts-utils \
    && rm -rf /var/lib/apt/lists/* && \
    fc-cache -fv

# Terminal rendering C/C++ development libraries
RUN apt-get update && apt-get install -y \
    libncurses-dev \
    libncursesw5-dev \
    ncurses-term \
    libncursesw6 \
    ncurses-doc \
    libslang2-dev \
    libnotcurses-dev \
    notcurses-bin \
    libvterm-dev \
    libtermkey-dev \
    libtickit-dev \
    libcaca-dev \
    caca-utils \
    libaa1-dev \
    aalib1 \
    libnewt-dev \
    libreadline-dev \
    libedit-dev \
    libunistring-dev \
    libunibilium-dev \
    libutf8proc-dev \
    libfmt-dev \
    dialog \
    whiptail \
    figlet \
    toilet \
    toilet-fonts \
    cowsay \
    boxes \
    fortune-mod \
    cmatrix \
    sl \
    lolcat \
    && rm -rf /var/lib/apt/lists/*

# Codecs: video, audio & image (ffmpeg codec dev libs — GStreamer dropped to save ~200 MB)
RUN apt-get update && apt-get install -y \
    libavcodec-extra \
    libx264-dev \
    libx265-dev \
    libvpx-dev \
    libopus-dev \
    libaom-dev \
    libdav1d-dev \
    libde265-dev \
    libtheora-dev \
    libspeex-dev \
    libmp3lame-dev \
    libogg-dev \
    libvorbis-dev \
    libflac-dev \
    libwavpack-dev \
    && rm -rf /var/lib/apt/lists/*

# Language packs (available but do NOT change the default LANG/LC_ALL)
# Default remains LANG=C.UTF-8 which already supports full Unicode/emoji
RUN apt-get update && apt-get install -y \
    language-pack-en \
    language-pack-he \
    language-pack-ar \
    language-pack-zh-hans \
    language-pack-ja \
    language-pack-ko \
    language-pack-ru \
    language-pack-fr \
    language-pack-de \
    language-pack-es \
    language-pack-pt \
    language-pack-hi \
    language-pack-it \
    language-pack-pl \
    language-pack-tr \
    language-pack-uk \
    && rm -rf /var/lib/apt/lists/*

# Generate locales (Hebrew, Arabic, and common)
# NOTE: Does NOT change the default locale (C.UTF-8), just makes these available
RUN locale-gen en_US.UTF-8 && \
    locale-gen he_IL.UTF-8 && \
    locale-gen ar_SA.UTF-8 && \
    locale-gen ru_RU.UTF-8 && \
    locale-gen fr_FR.UTF-8 && \
    locale-gen de_DE.UTF-8 && \
    locale-gen es_ES.UTF-8 && \
    locale-gen zh_CN.UTF-8 && \
    locale-gen ja_JP.UTF-8 && \
    locale-gen ko_KR.UTF-8 && \
    locale-gen hi_IN.UTF-8 && \
    locale-gen pt_BR.UTF-8 && \
    locale-gen it_IT.UTF-8 && \
    locale-gen pl_PL.UTF-8 && \
    locale-gen tr_TR.UTF-8 && \
    locale-gen uk_UA.UTF-8

# ============================================================
# TERMINAL AGENT TOOLS
# Tools that a CLI-based AI agent frequently uses
# ============================================================

# Agent essentials: search, text processing, structured data, automation
RUN apt-get update && apt-get install -y \
    silversearcher-ag \
    cloc \
    shellcheck \
    shfmt \
    expect \
    moreutils \
    inotify-tools \
    procps \
    util-linux \
    coreutils \
    groff \
    wdiff \
    highlight \
    source-highlight \
    pigz \
    pbzip2 \
    pixz \
    asciinema \
    direnv \
    apache2-utils \
    miller \
    csvtool \
    xml-twig-tools \
    html-xml-utils \
    neovim \
    micro \
    fish \
    btop \
    mc \
    ranger \
    nnn \
    vifm \
    trash-cli \
    xdg-utils \
    xclip \
    xsel \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI (gh) - essential for agents interacting with GitHub
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt-get update && apt-get install -y gh && \
    rm -rf /var/lib/apt/lists/*

# Modern CLI replacements (pre-built binaries)
# eza - modern ls with git integration, tree view, icons
RUN wget -qO- https://github.com/eza-community/eza/releases/latest/download/eza_x86_64-unknown-linux-gnu.tar.gz \
    | tar xz -C /usr/local/bin/

# delta - beautiful git diffs with syntax highlighting
RUN wget -qO /tmp/delta.deb https://github.com/dandavison/delta/releases/download/0.18.2/git-delta_0.18.2_amd64.deb && \
    dpkg -i /tmp/delta.deb && rm /tmp/delta.deb

# dust - modern du (disk usage)
RUN wget -qO /tmp/dust.deb https://github.com/bootandy/dust/releases/download/v1.1.1/du-dust_1.1.1-1_amd64.deb && \
    dpkg -i /tmp/dust.deb && rm /tmp/dust.deb

# duf - modern df (disk free)
RUN wget -qO /tmp/duf.deb https://github.com/muesli/duf/releases/download/v0.8.1/duf_0.8.1_linux_amd64.deb && \
    dpkg -i /tmp/duf.deb && rm /tmp/duf.deb

# glow - render Markdown in terminal
RUN wget -qO /tmp/glow.deb https://github.com/charmbracelet/glow/releases/download/v2.0.0/glow_2.0.0_amd64.deb && \
    dpkg -i /tmp/glow.deb && rm /tmp/glow.deb

# lazygit - TUI git client
RUN LAZYGIT_VERSION=$(curl -s "https://api.github.com/repos/jesseduffield/lazygit/releases/latest" | grep -Po '"tag_name": "v\K[^"]*') && \
    curl -Lo /tmp/lazygit.tar.gz "https://github.com/jesseduffield/lazygit/releases/latest/download/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz" && \
    tar xf /tmp/lazygit.tar.gz -C /usr/local/bin lazygit && rm /tmp/lazygit.tar.gz

# just - modern make alternative (task runner)
RUN wget -qO- https://just.systems/install.sh | bash -s -- --to /usr/local/bin

# hyperfine - CLI benchmarking tool
RUN wget -qO /tmp/hyperfine.deb https://github.com/sharkdp/hyperfine/releases/download/v1.19.0/hyperfine_1.19.0_amd64.deb && \
    dpkg -i /tmp/hyperfine.deb && rm /tmp/hyperfine.deb

# sd - modern sed replacement
RUN wget -qO /tmp/sd.tar.gz https://github.com/chmln/sd/releases/download/v1.0.0/sd-v1.0.0-x86_64-unknown-linux-gnu.tar.gz && \
    tar xf /tmp/sd.tar.gz -C /tmp && cp /tmp/sd-v1.0.0-x86_64-unknown-linux-gnu/sd /usr/local/bin/ && \
    chmod +x /usr/local/bin/sd && rm -rf /tmp/sd*

# tokei - fast code statistics
RUN wget -qO /tmp/tokei.tar.gz https://github.com/XAMPPRocky/tokei/releases/download/v12.1.2/tokei-x86_64-unknown-linux-gnu.tar.gz && \
    tar xf /tmp/tokei.tar.gz -C /usr/local/bin && chmod +x /usr/local/bin/tokei && rm /tmp/tokei.tar.gz

# gron - make JSON greppable
RUN wget -qO /tmp/gron.tar.gz https://github.com/tomnomnom/gron/releases/download/v0.7.1/gron-linux-amd64-0.7.1.tgz && \
    tar xf /tmp/gron.tar.gz -C /usr/local/bin && chmod +x /usr/local/bin/gron && rm /tmp/gron.tar.gz

# pup - jq for HTML (parse HTML from CLI)
RUN wget -qO /tmp/pup.zip https://github.com/ericchiang/pup/releases/download/v0.4.0/pup_v0.4.0_linux_amd64.zip && \
    unzip -o /tmp/pup.zip -d /usr/local/bin && chmod +x /usr/local/bin/pup && rm /tmp/pup.zip

# starship - cross-shell prompt (available but not set as default)
RUN curl -sS https://starship.rs/install.sh | sh -s -- --yes

# rclone - cloud storage swiss army knife
RUN curl -fsSL https://rclone.org/install.sh | bash

# Zellij - modern terminal multiplexer (available alongside tmux)
RUN wget -qO /tmp/zellij.tar.gz https://github.com/zellij-org/zellij/releases/latest/download/zellij-x86_64-unknown-linux-musl.tar.gz && \
    tar xf /tmp/zellij.tar.gz -C /usr/local/bin && chmod +x /usr/local/bin/zellij && rm /tmp/zellij.tar.gz

# Azure CLI (for Azure DevOps / TFS interaction)
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash && \
    rm -rf /var/lib/apt/lists/*

# Install Azure DevOps extension for az CLI
RUN az extension add --name azure-devops 2>/dev/null || true

# Additional language runtimes: Go, Rust toolchain support
RUN apt-get update && apt-get install -y \
    golang-go \
    rustc \
    cargo \
    ruby \
    ruby-dev \
    perl \
    lua5.4 \
    liblua5.4-dev \
    r-base-core \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# PYTHON PACKAGES (installed system-wide as root)
# ============================================================

# Fix ALL system packages that lack RECORD files (installed by apt, blocks pip upgrades)
# Find and remove every dist-info dir missing a RECORD file so pip can upgrade freely
RUN find /usr/lib/python3/dist-packages /usr/lib/python3.12/dist-packages \
        -name '*.dist-info' -type d ! -exec test -f '{}/RECORD' \; -exec rm -rf '{}' + 2>/dev/null; \
    pip3 install --break-system-packages --no-cache-dir setuptools wheel packaging charset-normalizer

# --- Data processing & analysis (core) ---
RUN pip3 install --break-system-packages --no-cache-dir \
    numpy \
    scipy \
    pandas \
    polars \
    pyarrow \
    dask[complete] \
    modin[dask] \
    xarray \
    sympy \
    statsmodels \
    more-itertools \
    toolz \
    cytoolz \
    joblib \
    orjson \
    ujson \
    pyyaml \
    toml \
    tomli \
    tomli-w \
    python-dateutil \
    arrow \
    pendulum \
    pytz \
    chardet \
    charset-normalizer \
    tabulate \
    prettytable \
    tqdm

# --- Data processing (accelerators & profiling) ---
RUN pip3 install --break-system-packages --no-cache-dir \
    numba \
    cython \
    numexpr \
    bottleneck \
    swifter \
    pandarallel

# --- Data quality, profiling & validation ---
RUN pip3 install --break-system-packages --no-cache-dir \
    missingno \
    ydata-profiling \
    sweetviz \
    pandera \
    great-expectations

# --- Data visualization (core) ---
RUN pip3 install --break-system-packages --no-cache-dir \
    matplotlib \
    seaborn \
    plotly \
    bokeh \
    altair \
    vega_datasets \
    pygal \
    wordcloud \
    graphviz \
    networkx \
    pydot

# --- Data visualization (advanced) ---
RUN pip3 install --break-system-packages --no-cache-dir \
    plotnine \
    holoviews \
    hvplot \
    datashader \
    colorcet \
    panel \
    streamlit \
    gradio \
    nicegui

# --- PDF reading, creation & manipulation ---
RUN pip3 install --break-system-packages --no-cache-dir \
    pypdf \
    PyPDF2 \
    pdfplumber \
    "pdfminer.six" \
    PyMuPDF \
    pikepdf \
    reportlab \
    fpdf2 \
    weasyprint \
    xhtml2pdf \
    borb \
    pdfrw \
    img2pdf \
    svglib \
    camelot-py[cv] \
    tabula-py \
    pdf2image \
    ocrmypdf \
    pdf2docx

# --- Hebrew / RTL / Bidi / Arabic text support ---
RUN pip3 install --break-system-packages --no-cache-dir \
    python-bidi \
    arabic-reshaper \
    PyICU \
    pyfribidi \
    hebrew-tokenizer \
    camel-tools

# --- Azure DevOps / TFS client ---
RUN pip3 install --break-system-packages --no-cache-dir \
    azure-devops \
    azure-cli-core \
    azure-identity \
    azure-storage-blob \
    azure-storage-file-share \
    msrest \
    msal

# --- Excel, Word, PowerPoint, document parsing & creation ---
RUN pip3 install --break-system-packages --no-cache-dir \
    openpyxl \
    xlrd \
    xlsxwriter \
    xlwt \
    odfpy \
    python-docx \
    python-pptx \
    python-calamine \
    mammoth \
    docx2txt \
    striprtf \
    ebooklib \
    csvkit \
    petl

# --- File & document conversion ---
RUN pip3 install --break-system-packages --no-cache-dir \
    pypandoc \
    markdownify \
    html2text \
    filetype \
    python-magic \
    xmltodict \
    dicttoxml

# --- Video, audio & multimedia (Python wrappers) ---
RUN pip3 install --break-system-packages --no-cache-dir \
    moviepy \
    ffmpeg-python \
    pydub \
    librosa \
    soundfile \
    audioread \
    imageio-ffmpeg

# --- OCR & image processing ---
RUN pip3 install --break-system-packages --no-cache-dir \
    pytesseract \
    Pillow \
    opencv-python-headless \
    scikit-image \
    rawpy \
    imageio \
    Wand \
    albumentations \
    imgaug

# --- PyTorch CPU-only (installed first to prevent 700 MB+ default wheel) ---
RUN pip3 install --break-system-packages --no-cache-dir \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cpu

# --- OCR (depends on torch) ---
RUN pip3 install --break-system-packages --no-cache-dir --no-deps \
    easyocr
RUN pip3 install --break-system-packages --no-cache-dir \
    easyocr

# --- Search, retrieval & ranking (BM25, vector search, etc.) ---
RUN pip3 install --break-system-packages --no-cache-dir \
    rank-bm25 \
    whoosh \
    lunr \
    faiss-cpu \
    annoy \
    hnswlib \
    chromadb \
    sentence-transformers \
    txtai

# --- LLM / AI client libraries ---
RUN pip3 install --break-system-packages --no-cache-dir \
    openai \
    anthropic \
    huggingface-hub \
    datasets \
    transformers \
    tokenizers \
    sentencepiece \
    tiktoken \
    onnx \
    onnxruntime

# --- Machine learning (core) ---
RUN pip3 install --break-system-packages --no-cache-dir \
    scikit-learn \
    xgboost \
    lightgbm \
    catboost \
    imbalanced-learn \
    feature-engine \
    category_encoders

# --- ML: hyperparameter tuning & explainability ---
RUN pip3 install --break-system-packages --no-cache-dir \
    optuna \
    hyperopt \
    shap \
    lime \
    eli5 \
    mlflow

# --- NLP & text processing ---
RUN pip3 install --break-system-packages --no-cache-dir \
    nltk \
    spacy \
    gensim \
    textblob \
    langdetect \
    regex \
    rapidfuzz \
    fuzzywuzzy[speedup] \
    ftfy \
    unidecode \
    python-Levenshtein \
    chardet \
    polyglot \
    wordfreq

# --- Statistics & scientific ---
RUN pip3 install --break-system-packages --no-cache-dir \
    pingouin \
    lifelines \
    arviz \
    emcee \
    uncertainties

# --- Web, HTTP & scraping ---
RUN pip3 install --break-system-packages --no-cache-dir \
    requests \
    httpx[http2] \
    aiohttp \
    beautifulsoup4 \
    lxml \
    cssselect \
    html5lib \
    scrapy \
    parsel \
    feedparser \
    urllib3 \
    selenium \
    playwright \
    pyppeteer \
    splinter \
    mechanicalsoup \
    grab \
    httpcore

# --- HTML rendering, parsing, validation & normalization ---
RUN pip3 install --break-system-packages --no-cache-dir \
    html5-parser \
    bleach \
    nh3 \
    selectolax \
    pyquery \
    tinycss2 \
    cssutils \
    css-parser \
    premailer \
    html2text \
    markdownify \
    html-sanitizer \
    htmlmin \
    minify-html \
    lxml-html-clean \
    readability-lxml \
    trafilatura \
    newspaper3k \
    boilerpy3 \
    w3lib \
    tldextract \
    validators

# --- Database & ORM ---
RUN pip3 install --break-system-packages --no-cache-dir \
    sqlalchemy \
    alembic \
    psycopg2-binary \
    asyncpg \
    redis \
    pymongo \
    motor \
    peewee \
    dataset \
    databases[sqlite,postgresql] \
    duckdb \
    lancedb

# --- Web frameworks, servers & dashboards ---
RUN pip3 install --break-system-packages --no-cache-dir \
    flask \
    flask-cors \
    flask-sqlalchemy \
    flask-login \
    flask-wtf \
    flask-restful \
    flask-socketio \
    flask-talisman \
    django \
    django-cors-headers \
    djangorestframework \
    fastapi \
    uvicorn[standard] \
    starlette \
    gunicorn \
    dash \
    tornado \
    aiofiles \
    websockets \
    waitress \
    hypercorn \
    daphne \
    twisted \
    sanic \
    falcon \
    bottle \
    cherrypy \
    pyramid \
    hug \
    responder \
    werkzeug \
    httptools \
    h11 \
    h2 \
    wsproto \
    uvloop \
    python-socketio \
    channels \
    gevent \
    eventlet \
    pyopenssl \
    trustme

# --- CLI, terminal & formatting ---
RUN pip3 install --break-system-packages --no-cache-dir \
    click \
    typer \
    rich \
    pydantic \
    loguru \
    structlog \
    tenacity \
    retry \
    environs \
    colorama \
    termcolor \
    blessed \
    prompt-toolkit \
    questionary \
    alive-progress \
    halo \
    yaspin \
    humanize \
    inflect \
    natsort \
    semver \
    packaging

# --- Terminal UI / TUI frameworks & rendering ---
RUN pip3 install --break-system-packages --no-cache-dir \
    textual \
    textual-dev \
    urwid \
    npyscreen \
    asciimatics \
    pytermgui \
    py-cui \
    curtsies \
    wcwidth \
    emoji \
    unicodedata2 \
    pyfiglet \
    art \
    asciichartpy \
    plotext \
    drawille \
    colored \
    blessings \
    sty \
    ansicolors \
    colorful \
    pastel \
    termtables \
    tabulate \
    terminaltables

# --- Dev tools, linting & formatting ---
RUN pip3 install --break-system-packages --no-cache-dir \
    tox \
    nox \
    black \
    ruff \
    isort \
    flake8 \
    mypy \
    pylint \
    bandit \
    safety \
    vulture \
    pyflakes \
    autopep8 \
    yapf \
    pre-commit

# --- Testing ---
RUN pip3 install --break-system-packages --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-asyncio \
    pytest-xdist \
    pytest-mock \
    pytest-benchmark \
    hypothesis \
    coverage \
    faker \
    factory-boy \
    responses \
    vcrpy \
    freezegun \
    time-machine

# --- Profiling & debugging ---
RUN pip3 install --break-system-packages --no-cache-dir \
    ipython \
    ipdb \
    pygments \
    memory-profiler \
    line-profiler \
    scalene \
    snakeviz \
    py-spy \
    objgraph \
    pympler

# --- Jupyter ecosystem ---
RUN pip3 install --break-system-packages --no-cache-dir \
    jupyter \
    jupyterlab \
    notebook \
    nbconvert \
    nbformat \
    ipywidgets \
    ipykernel \
    jupytext \
    papermill \
    nbstripout

# --- Crypto, TLS, hashing & security ---
RUN pip3 install --break-system-packages --no-cache-dir \
    cryptography \
    pyopenssl \
    pynacl \
    pycryptodome \
    pycryptodomex \
    bcrypt \
    argon2-cffi \
    passlib \
    hashids \
    pyjwt \
    python-jose[cryptography] \
    itsdangerous \
    fernet \
    asn1crypto \
    pyotp \
    qrcode \
    keyring \
    paramiko \
    fabric \
    python-gnupg \
    certifi \
    cffi \
    truststore \
    certvalidator \
    oscrypto \
    tls-parser \
    sslscan \
    sslyze \
    tlslite-ng \
    scrypt \
    jwcrypto \
    secrets-manager

# --- Geospatial ---
RUN pip3 install --break-system-packages --no-cache-dir \
    shapely \
    geopandas \
    folium \
    pyproj \
    fiona \
    rasterio \
    geopy

# --- Cloud, API & task orchestration ---
RUN pip3 install --break-system-packages --no-cache-dir \
    boto3 \
    google-cloud-storage \
    python-dotenv \
    python-multipart \
    jinja2 \
    mako \
    markdown \
    python-markdown-math \
    celery \
    dramatiq \
    apscheduler \
    watchdog \
    luigi \
    prefect

# --- Serialization, compression & data formats ---
RUN pip3 install --break-system-packages --no-cache-dir \
    h5py \
    tables \
    fastparquet \
    msgpack \
    cbor2 \
    protobuf \
    flatbuffers \
    lz4 \
    zstandard \
    brotli \
    python-snappy \
    avro-python3 \
    fastavro

# --- Config, schema & data classes ---
RUN pip3 install --break-system-packages --no-cache-dir \
    attrs \
    cattrs \
    dataclasses-json \
    marshmallow \
    cerberus \
    dynaconf \
    python-decouple \
    omegaconf \
    hydra-core \
    typeguard \
    beartype

# --- Shell, process & system utilities ---
RUN pip3 install --break-system-packages --no-cache-dir \
    sh \
    plumbum \
    invoke \
    doit \
    psutil \
    supervisor

# --- Git & VCS ---
RUN pip3 install --break-system-packages --no-cache-dir \
    gitpython \
    pygithub \
    dulwich

# --- Caching ---
RUN pip3 install --break-system-packages --no-cache-dir \
    cachetools \
    diskcache \
    dogpile.cache \
    aiocache

# --- Async ---
RUN pip3 install --break-system-packages --no-cache-dir \
    trio \
    anyio \
    asyncpg

# --- Extra general-purpose utilities ---
RUN pip3 install --break-system-packages --no-cache-dir \
    boltons \
    funcy \
    pydash \
    returns \
    toolz \
    multipledispatch \
    bidict \
    sortedcontainers \
    intervaltree \
    bitarray \
    mmh3 \
    xxhash \
    pybloom-live \
    datasketch

# --- Financial & time series ---
RUN pip3 install --break-system-packages --no-cache-dir \
    yfinance \
    pandas-ta \
    prophet \
    arch \
    pmdarima \
    tslearn \
    sktime

# --- PCAP, packet analysis & network forensics ---
RUN pip3 install --break-system-packages --no-cache-dir \
    scapy \
    dpkt \
    pyshark \
    kamene \
    pcapng \
    python-pcapng \
    impacket \
    netaddr \
    ipaddress \
    netifaces

# --- Agent tools: interactive REPLs & enhanced shells ---
RUN pip3 install --break-system-packages --no-cache-dir \
    bpython \
    ptpython \
    xonsh \
    ipython \
    jupyter-console

# --- Agent tools: database CLIs (interactive) ---
RUN pip3 install --break-system-packages --no-cache-dir \
    litecli \
    pgcli \
    mycli \
    iredis

# --- Agent tools: system monitoring & process management ---
RUN pip3 install --break-system-packages --no-cache-dir \
    glances \
    ansible \
    ansible-lint \
    molecule

# --- Agent tools: CLI helpers & productivity ---
RUN pip3 install --break-system-packages --no-cache-dir \
    tldr \
    howdoi \
    thefuck \
    cookiecutter \
    copier \
    cruft \
    bump2version \
    semantic-version \
    twine \
    build \
    flit \
    hatch \
    pdm \
    poetry

# --- Agent tools: code generation, scaffolding & API ---
RUN pip3 install --break-system-packages --no-cache-dir \
    openapi-spec-validator \
    jsonschema \
    prance \
    apispec \
    flasgger \
    datamodel-code-generator \
    sqlacodegen \
    alembic \
    cookiecutter

# --- Agent tools: file watching, diffing & patching ---
RUN pip3 install --break-system-packages --no-cache-dir \
    watchfiles \
    inotify-simple \
    deepdiff \
    dictdiffer \
    jsonpatch \
    jsonpointer \
    unidiff \
    patch-ng

# --- Agent tools: subprocess, expect & automation ---
RUN pip3 install --break-system-packages --no-cache-dir \
    pexpect \
    ptyprocess \
    sarge \
    delegator.py \
    python-crontab \
    schedule \
    rq \
    huey

# Download NLTK data (common corpora for offline use)
RUN python3 -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('averaged_perceptron_tagger'); nltk.download('averaged_perceptron_tagger_eng'); nltk.download('vader_lexicon'); nltk.download('maxent_ne_chunker'); nltk.download('maxent_ne_chunker_tab'); nltk.download('words'); nltk.download('omw-1.4'); nltk.download('universal_tagset')"

# Download spaCy models for offline use (PIP_BREAK_SYSTEM_PACKAGES bypasses PEP 668)
RUN PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m spacy download en_core_web_sm && \
    PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m spacy download en_core_web_md

# Install Playwright browsers (Chromium + Firefox) for headless browser automation
# This pre-downloads browser binaries so they work offline
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
RUN playwright install --with-deps chromium firefox

# Puppeteer: skip its own Chromium download, reuse Playwright's (~400 MB saved)
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/opt/playwright-browsers/chromium-*/chrome-linux/chrome

# Make browser binaries accessible to all users
RUN chmod -R a+rX /opt/playwright-browsers

# Create convenience symlinks for Ubuntu-renamed binaries
RUN ln -sf /usr/bin/fdfind /usr/local/bin/fd && \
    ln -sf /usr/bin/batcat /usr/local/bin/bat

# Build ttyd from source for OSC 52 clipboard support
# Released 1.7.7 bundles xterm.js 5.4.0 without the clipboard addon.
# Commit 9c87671 on main includes @xterm/addon-clipboard for OSC 52 browser clipboard.
RUN apt-get update && apt-get install -y \
    libjson-c-dev \
    libuv1-dev \
    && rm -rf /var/lib/apt/lists/*

# Build libwebsockets 4.3.6 with libuv support (required by ttyd)
RUN git clone --depth 1 --branch v4.3.6 https://github.com/warmcat/libwebsockets.git /tmp/lws && \
    mkdir /tmp/lws/build && cd /tmp/lws/build && \
    cmake .. \
        -DLWS_WITH_LIBUV=ON \
        -DLWS_WITHOUT_CLIENT=ON \
        -DLWS_WITH_HTTP2=ON \
        -DCMAKE_BUILD_TYPE=Release && \
    make -j$(nproc) && make install && ldconfig && \
    rm -rf /tmp/lws

# Build ttyd: frontend (xterm.js 5.5.0 + clipboard addon) then C backend
RUN git clone https://github.com/tsl0922/ttyd.git /tmp/ttyd && \
    cd /tmp/ttyd && git checkout 9c87671ccae9eefa3c01b08169272c0922e7cdff && \
    npm install -g corepack && corepack enable && \
    cd /tmp/ttyd/html && yarn install && yarn build && \
    mkdir /tmp/ttyd/build && cd /tmp/ttyd/build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    make -j$(nproc) && \
    cp ttyd /usr/local/bin/ttyd && \
    rm -rf /tmp/ttyd

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

# Install Vibe CLI v2.0.2 from source with streaming disabled
# Streaming breaks tool calls with Ollama/vLLM backends (GitHub issue #252)
# Patch: cli.py line 174: enable_streaming=True -> enable_streaming=False
RUN git clone --branch v2.0.2 --depth 1 https://github.com/mistralai/vibe.git /tmp/vibe \
    && sed -i 's/enable_streaming=True/enable_streaming=False/' /tmp/vibe/vibe/cli/cli.py \
    && /home/vibe/.local/bin/uv tool install /tmp/vibe \
    && rm -rf /tmp/vibe

# Create vibe config directory
RUN mkdir -p /home/vibe/.vibe

# Copy vibe configuration (will be added at build time)
COPY --chown=vibe:vibe config/vibe-config.toml /home/vibe/.vibe/config.toml
COPY --chown=vibe:vibe config/vibe-env /home/vibe/.vibe/.env
# Pre-trust workspace folder so AGENTS.md is auto-loaded
COPY --chown=vibe:vibe config/vibe-trusted-folders.toml /home/vibe/.vibe/trusted_folders.toml

# Copy session startup script (for persistent tmux sessions)
COPY --chown=vibe:vibe config/start-session.sh /home/vibe/.local/bin/start-session.sh
RUN chmod +x /home/vibe/.local/bin/start-session.sh

# Copy tmux configuration
COPY --chown=vibe:vibe config/tmux.conf /home/vibe/.tmux.conf

# Create workspace directory for user files
RUN mkdir -p /home/vibe/workspace

# Copy AGENTS.md to workspace (auto-loaded by Vibe v2.x when folder is trusted)
COPY --chown=vibe:vibe config/AGENTS.md /home/vibe/workspace/AGENTS.md

# Create a nice bashrc
RUN echo 'export PS1="\[\033[1;32m\]\u@vibe-terminal\[\033[0m\]:\[\033[1;34m\]\w\[\033[0m\]\$ "' >> /home/vibe/.bashrc \
    && echo 'alias ll="ls -la"' >> /home/vibe/.bashrc \
    && echo 'alias la="ls -A"' >> /home/vibe/.bashrc \
    && echo 'export PATH="/home/vibe/.local/bin:$PATH"' >> /home/vibe/.bashrc \
    && echo 'export PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers' >> /home/vibe/.bashrc \
    && echo 'export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true' >> /home/vibe/.bashrc \
    && echo 'cd /home/vibe/workspace' >> /home/vibe/.bashrc \
    && echo '' >> /home/vibe/.bashrc \
    && echo '# Welcome message' >> /home/vibe/.bashrc \
    && echo 'echo ""' >> /home/vibe/.bashrc \
    && echo 'echo "Welcome to Vibe Terminal!"' >> /home/vibe/.bashrc \
    && echo 'echo ""' >> /home/vibe/.bashrc \
    && echo 'echo "Copy tips:"' >> /home/vibe/.bashrc \
    && echo 'echo "  Drag to select               Auto-copies to clipboard (OSC 52)"' >> /home/vibe/.bashrc \
    && echo 'echo "  Shift + drag                 Native browser text selection"' >> /home/vibe/.bashrc \
    && echo 'echo "  Scroll wheel                 Scroll terminal history"' >> /home/vibe/.bashrc \
    && echo 'echo ""' >> /home/vibe/.bashrc \
    && echo 'echo "- Type \"vibe\" to start Mistral Vibe CLI"' >> /home/vibe/.bashrc \
    && echo 'echo "- Your workspace is /home/vibe/workspace"' >> /home/vibe/.bashrc \
    && echo 'echo "- Password for sudo: password"' >> /home/vibe/.bashrc \
    && echo 'echo ""' >> /home/vibe/.bashrc

WORKDIR /home/vibe/workspace

# Expose ttyd port
EXPOSE 7681

# Default command: start ttyd with persistent tmux session
# -W: Writable (allow client input)
# -p 7681: Port
# -t fontSize=14: Font size
# -t scrollback=10000: 10k line scrollback
# -t cursorStyle=bar: Bar cursor
# -t cursorBlink=true: Blinking cursor
# Uses start-session.sh to maintain tmux session across page refreshes
CMD ["/usr/local/bin/ttyd", "-W", "-p", "7681", "-t", "fontSize=14", "-t", "scrollback=10000", "-t", "cursorStyle=bar", "-t", "cursorBlink=true", "/home/vibe/.local/bin/start-session.sh"]
