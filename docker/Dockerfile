# Ubuntu-based terminal container with OpenCode CLI (+ Vibe CLI)
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm-256color
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# ============================================================
# SYSTEM PACKAGES (consolidated into larger groups)
# ============================================================

# Core utilities, shells, version control, network tools
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
    psmisc \
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
    git \
    git-lfs \
    gitk \
    git-gui \
    git-svn \
    git-doc \
    tig \
    subversion \
    mercurial \
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
    apt-transport-https \
    gnupg2 \
    wireguard-tools \
    openvpn \
    sshpass \
    sshfs \
    && rm -rf /var/lib/apt/lists/*

# Build toolchain, compilers, debugging tools, embedded dev
# (clang/clang-format/clang-tidy only — full LLVM/lldb/lld/libc++ dropped to save ~300 MB)
# (kept arm-none-eabi + aarch64; dropped armhf + riscv64 + qemu-system-misc to save ~300 MB)
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
    linux-tools-common \
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

# Buildroot & Yocto dependencies
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
    diffstat \
    chrpath \
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
    gcc-multilib \
    g++-multilib \
    lib32z1-dev \
    libc6-dev-i386 \
    pylint \
    rpcsvc-proto \
    lz4 \
    && rm -rf /var/lib/apt/lists/*

# Network packet analysis (wireshark-common includes editcap, mergecap, capinfos, etc.)
# Deep pcap analysis: termshark (TUI wireshark), tcptrace, tcpstat, ssldump, tcpick,
#   tcpxtract/foremost (file extraction), chaosreader/httpry (session reconstruction),
#   netsniff-ng (high-perf toolkit), zeek (protocol logs from pcap), suricata (offline IDS),
#   nfdump/argus-client (flow analysis), p0f (passive fingerprinting), sngrep (SIP/VoIP),
#   dnstop (DNS analysis), hping3 (packet crafting), dsniff (network audit suite)
# Python, Node.js, headless browser deps (Playwright provides its own Chromium)
# Java Runtime (JRE only — JDK dropped to save ~50 MB; only needed for tabula-py)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    libpcap-dev \
    tshark \
    wireshark-common \
    wireshark-doc \
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
    termshark \
    tcptrace \
    tcpstat \
    ssldump \
    tcpick \
    tcpxtract \
    chaosreader \
    foremost \
    httpry \
    netsniff-ng \
    hping3 \
    p0f \
    dsniff \
    sngrep \
    dnstop \
    nbtscan \
    httping \
    nfdump \
    argus-client \
    suricata \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    nodejs \
    npm \
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
    tidy \
    libxml2-utils \
    xmlstarlet \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Bun JavaScript/TypeScript runtime
RUN curl -fsSL https://bun.sh/install | BUN_INSTALL=/usr/local bash

# npm packages (browser automation, scraping, utilities, dev tools)
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
    @mermaid-js/mermaid-cli \
    md-to-pdf \
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
    debug \
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

# Libraries: image processing, PDF, graphics, ICU, crypto, OCR, documents
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
    poppler-utils \
    libpoppler-dev \
    libpoppler-cpp-dev \
    ghostscript \
    qpdf \
    pandoc \
    wkhtmltopdf \
    sqlite3 \
    libsqlite3-dev \
    postgresql-client \
    libpq-dev \
    redis-tools \
    liblapack-dev \
    libblas-dev \
    libopenblas-dev \
    libhdf5-dev \
    libgeos-dev \
    libproj-dev \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# LibreOffice (minimal: writer + calc for doc conversion, dropped impress + draw to save ~600 MB)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*

# Multimedia, audio, video, graphs, fonts
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
    graphviz \
    libgraphviz-dev \
    gnuplot \
    fonts-dejavu \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    fonts-liberation \
    fonts-liberation2 \
    fonts-noto \
    fonts-noto-color-emoji \
    fonts-noto-mono \
    fonts-noto-extra \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fonts-noto-ui-core \
    fonts-noto-ui-extra \
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
    fonts-ibm-plex \
    fonts-cantarell \
    fonts-crosextra-carlito \
    fonts-crosextra-caladea \
    fonts-nanum \
    fonts-nanum-coding \
    fonts-nanum-eco \
    fonts-nanum-extra \
    fonts-urw-base35 \
    fonts-sil-gentium-basic \
    fonts-sil-charis \
    fonts-wqy-microhei \
    fonts-wqy-zenhei \
    fonts-arphic-ukai \
    fonts-arphic-uming \
    fonts-ipafont-gothic \
    fonts-ipafont-mincho \
    fonts-vlgothic \
    fonts-takao-gothic \
    fonts-unfonts-core \
    fonts-unfonts-extra \
    fonts-sil-padauk \
    fonts-sil-abyssinica \
    fonts-lklug-sinhala \
    fonts-tibetan-machine \
    fonts-guru \
    fonts-guru-extra \
    fonts-lohit-guru \
    fonts-tlwg-garuda \
    fonts-tlwg-kinnari \
    fonts-tlwg-laksaman \
    fonts-tlwg-loma \
    fonts-tlwg-mono \
    fonts-tlwg-norasi \
    fonts-tlwg-purisa \
    fonts-tlwg-sawasdee \
    fonts-tlwg-typewriter \
    fonts-tlwg-typist \
    fonts-tlwg-typo \
    fonts-tlwg-umpush \
    fonts-tlwg-waree \
    xfonts-utils \
    && rm -rf /var/lib/apt/lists/* && fc-cache -fv

# PlantUML (uses graphviz + default-jre-headless already installed above)
RUN curl -fsSL -o /usr/local/lib/plantuml.jar \
      https://github.com/plantuml/plantuml/releases/download/v1.2025.0/plantuml-1.2025.0.jar \
    && printf '#!/bin/sh\nexec java -jar /usr/local/lib/plantuml.jar "$@"\n' > /usr/local/bin/plantuml \
    && chmod +x /usr/local/bin/plantuml

# Terminal libraries, codecs (GStreamer dropped to save ~200 MB), language packs
# Language packs available but do NOT change the default LANG/LC_ALL (C.UTF-8 supports full Unicode/emoji)
RUN apt-get update && apt-get install -y \
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
RUN locale-gen en_US.UTF-8 he_IL.UTF-8 ar_SA.UTF-8 ru_RU.UTF-8 fr_FR.UTF-8 \
    de_DE.UTF-8 es_ES.UTF-8 zh_CN.UTF-8 ja_JP.UTF-8 ko_KR.UTF-8 \
    hi_IN.UTF-8 pt_BR.UTF-8 it_IT.UTF-8 pl_PL.UTF-8 tr_TR.UTF-8 uk_UA.UTF-8

# ============================================================
# TERMINAL AGENT TOOLS
# Tools that a CLI-based AI agent frequently uses
# ============================================================

# Agent essentials: search, text processing, structured data, automation, language runtimes
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
    xclip \
    xsel \
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

# GitHub CLI (gh) - essential for agents interacting with GitHub
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt-get update && apt-get install -y gh && \
    rm -rf /var/lib/apt/lists/*

# glow (Charmbracelet — markdown reader)
RUN wget -qO /tmp/glow.deb https://github.com/charmbracelet/glow/releases/download/v2.0.0/glow_2.0.0_amd64.deb && dpkg -i /tmp/glow.deb && rm /tmp/glow.deb

# rclone (cloud storage swiss army knife)
RUN curl -fsSL https://rclone.org/install.sh | bash

# Azure CLI
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash && \
    rm -rf /var/lib/apt/lists/* && \
    az extension add --name azure-devops 2>/dev/null || true

# ============================================================
# PYTHON PACKAGES (consolidated into larger groups)
# ============================================================

# Fix system packages and install base
RUN find /usr/lib/python3/dist-packages /usr/lib/python3.12/dist-packages \
        -name '*.dist-info' -type d ! -exec test -f '{}/RECORD' \; -exec rm -rf '{}' + 2>/dev/null; \
    pip3 install --break-system-packages --no-cache-dir setuptools wheel packaging charset-normalizer

# Data processing, analysis, visualization
RUN pip3 install --break-system-packages --no-cache-dir \
    numpy scipy pandas polars pyarrow "dask[complete]" "modin[dask]" xarray sympy statsmodels \
    more-itertools toolz cytoolz joblib orjson ujson pyyaml toml tomli tomli-w \
    python-dateutil arrow pendulum pytz chardet charset-normalizer tabulate prettytable tqdm \
    numba cython numexpr bottleneck swifter pandarallel \
    missingno ydata-profiling sweetviz pandera great-expectations \
    matplotlib seaborn plotly bokeh altair vega_datasets pygal wordcloud graphviz networkx pydot \
    plotnine holoviews hvplot datashader colorcet panel streamlit gradio nicegui

# PDF, documents, RTL text, Azure, Office formats
RUN pip3 install --break-system-packages --no-cache-dir \
    pypdf PyPDF2 pdfplumber "pdfminer.six" PyMuPDF pikepdf reportlab fpdf2 weasyprint xhtml2pdf \
    borb pdfrw img2pdf svglib "camelot-py[cv]" tabula-py pdf2image ocrmypdf pdf2docx \
    python-bidi arabic-reshaper PyICU pyfribidi hebrew-tokenizer camel-tools \
    azure-devops azure-cli-core azure-identity azure-storage-blob azure-storage-file-share msrest msal \
    openpyxl xlrd xlsxwriter xlwt odfpy python-docx python-pptx python-calamine mammoth docx2txt striprtf ebooklib csvkit petl \
    pypandoc markdownify html2text filetype python-magic xmltodict dicttoxml \
    mwclient mwparserfromhell wikitextparser

# Multimedia, OCR, image processing
RUN pip3 install --break-system-packages --no-cache-dir \
    moviepy ffmpeg-python pydub librosa soundfile audioread imageio-ffmpeg \
    pytesseract Pillow opencv-python-headless scikit-image rawpy imageio Wand albumentations imgaug

# PyTorch CPU-only (installed first to prevent 700 MB+ default wheel)
RUN pip3 install --break-system-packages --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# OCR, search, LLM, ML
RUN pip3 install --break-system-packages --no-cache-dir --no-deps easyocr && \
    pip3 install --break-system-packages --no-cache-dir easyocr \
    rank-bm25 whoosh lunr faiss-cpu annoy hnswlib chromadb sentence-transformers txtai \
    openai anthropic huggingface-hub datasets transformers tokenizers sentencepiece tiktoken onnx onnxruntime \
    scikit-learn xgboost lightgbm catboost imbalanced-learn feature-engine category_encoders \
    optuna hyperopt shap lime eli5 mlflow

# NLP, statistics, web scraping
RUN pip3 install --break-system-packages --no-cache-dir \
    nltk spacy gensim textblob langdetect regex rapidfuzz "fuzzywuzzy[speedup]" ftfy unidecode python-Levenshtein polyglot wordfreq \
    pingouin lifelines arviz emcee uncertainties \
    requests "httpx[http2]" aiohttp beautifulsoup4 lxml cssselect html5lib scrapy parsel feedparser urllib3 \
    selenium playwright pyppeteer splinter mechanicalsoup grab httpcore

# HTML parsing, database, web frameworks
RUN pip3 install --break-system-packages --no-cache-dir \
    html5-parser bleach nh3 selectolax pyquery tinycss2 cssutils css-parser premailer \
    html-sanitizer htmlmin minify-html lxml-html-clean readability-lxml trafilatura newspaper3k boilerpy3 w3lib tldextract validators \
    sqlalchemy alembic psycopg2-binary asyncpg redis pymongo motor peewee dataset "databases[sqlite,postgresql]" duckdb lancedb \
    flask flask-cors flask-sqlalchemy flask-login flask-wtf flask-restful flask-socketio flask-talisman \
    django django-cors-headers djangorestframework fastapi "uvicorn[standard]" starlette gunicorn dash tornado \
    aiofiles websockets waitress hypercorn daphne twisted sanic falcon bottle cherrypy pyramid hug responder \
    werkzeug httptools h11 h2 wsproto uvloop python-socketio channels gevent eventlet pyopenssl trustme

# CLI, TUI, dev tools, testing, profiling, Jupyter
RUN pip3 install --break-system-packages --no-cache-dir \
    click typer rich pydantic loguru structlog tenacity retry environs colorama termcolor blessed \
    prompt-toolkit questionary alive-progress halo yaspin humanize inflect natsort semver \
    textual textual-dev urwid npyscreen asciimatics pytermgui py-cui curtsies wcwidth emoji unicodedata2 \
    pyfiglet art asciichartpy plotext drawille colored blessings sty ansicolors colorful pastel termtables terminaltables \
    tox nox black ruff isort flake8 mypy pylint bandit safety vulture pyflakes autopep8 yapf pre-commit \
    pytest pytest-cov pytest-asyncio pytest-xdist pytest-mock pytest-benchmark hypothesis coverage faker factory-boy responses vcrpy freezegun time-machine \
    ipython ipdb pygments memory-profiler line-profiler scalene snakeviz py-spy objgraph pympler \
    jupyter jupyterlab notebook nbconvert nbformat ipywidgets ipykernel jupytext papermill nbstripout

# Crypto, geo, cloud, serialization, config, utilities
RUN pip3 install --break-system-packages --no-cache-dir \
    cryptography pynacl pycryptodome pycryptodomex bcrypt argon2-cffi passlib hashids pyjwt "python-jose[cryptography]" \
    itsdangerous fernet asn1crypto pyotp qrcode keyring paramiko fabric python-gnupg certifi cffi \
    truststore certvalidator oscrypto tls-parser sslscan sslyze tlslite-ng scrypt jwcrypto secrets-manager \
    shapely geopandas folium pyproj fiona rasterio geopy \
    boto3 google-cloud-storage python-dotenv python-multipart jinja2 mako markdown python-markdown-math celery dramatiq apscheduler watchdog luigi prefect \
    h5py tables fastparquet msgpack cbor2 protobuf flatbuffers lz4 zstandard brotli python-snappy avro-python3 fastavro \
    attrs cattrs dataclasses-json marshmallow cerberus dynaconf python-decouple omegaconf hydra-core typeguard beartype \
    sh plumbum invoke doit psutil supervisor gitpython pygithub dulwich \
    cachetools diskcache dogpile.cache aiocache trio anyio \
    boltons funcy pydash returns multipledispatch bidict sortedcontainers intervaltree bitarray mmh3 xxhash pybloom-live datasketch

# Financial, PCAP, agent tools
RUN pip3 install --break-system-packages --no-cache-dir \
    yfinance pandas-ta prophet arch pmdarima tslearn sktime \
    scapy dpkt pyshark kamene pcapng python-pcapng impacket netaddr ipaddress netifaces nfstream \
    bpython ptpython xonsh jupyter-console litecli pgcli mycli iredis \
    glances ansible ansible-lint molecule \
    tldr howdoi thefuck cookiecutter copier cruft bump2version semantic-version twine build flit hatch pdm poetry \
    openapi-spec-validator jsonschema prance apispec flasgger datamodel-code-generator sqlacodegen \
    watchfiles inotify-simple deepdiff dictdiffer jsonpatch jsonpointer unidiff patch-ng \
    pexpect ptyprocess sarge delegator.py python-crontab schedule rq huey

# Download NLTK data & spaCy models
RUN python3 -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('averaged_perceptron_tagger'); nltk.download('averaged_perceptron_tagger_eng'); nltk.download('vader_lexicon'); nltk.download('maxent_ne_chunker'); nltk.download('maxent_ne_chunker_tab'); nltk.download('words'); nltk.download('omw-1.4'); nltk.download('universal_tagset')" && \
    PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m spacy download en_core_web_sm && \
    PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m spacy download en_core_web_md

# Install Playwright browsers (Chromium + Firefox) for headless browser automation
# This pre-downloads browser binaries so they work offline
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
RUN playwright install --with-deps chromium firefox && \
    npx playwright install chromium firefox && \
    chmod -R a+rX /opt/playwright-browsers

# Puppeteer: skip its own Chromium download, reuse Playwright's (~400 MB saved)
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/opt/playwright-browsers/chromium-*/chrome-linux/chrome

# Convenience symlinks
RUN ln -sf /usr/bin/fdfind /usr/local/bin/fd && \
    ln -sf /usr/bin/batcat /usr/local/bin/bat

# ============================================================
# BUILD TTYD FROM SOURCE
# ============================================================
# Build ttyd from source for OSC 52 clipboard support.
# Released 1.7.7 bundles xterm.js 5.4.0 without the clipboard addon.
# Commit 9c87671 on main includes @xterm/addon-clipboard for OSC 52 browser clipboard.

# ttyd build dependencies
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
# Commit 9c87671 includes @xterm/addon-clipboard for OSC 52 browser clipboard
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

# ============================================================
# USER SETUP
# ============================================================

# Create user with password "password"
# Use UID 1000 to match typical host user - enables seamless file sharing
# Ubuntu 24.04 has an "ubuntu" user with UID 1000, so remove it first
RUN userdel -r ubuntu 2>/dev/null || true \
    && useradd -m -s /bin/bash -G sudo -u 1000 vibe \
    && echo "vibe:password" | chpasswd \
    && echo "vibe ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to vibe user for installations
USER vibe
WORKDIR /home/vibe

# Install uv for vibe user
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/vibe/.local/bin:$PATH"

# Copy system prompt suffix (environment context to append to cli.md)
COPY config/vibe/system-prompt-suffix.md /tmp/system-prompt-suffix.md

# Install Vibe CLI v2.0.2 from source with patch:
# Append Docker environment context to system prompt (cli.md)
# NOTE: Response streaming causes significant delay (~2x slower token display),
# but disabling it triggers race conditions within Vibe's async code, so we keep it.
# To disable streaming, add before uv install: sed -i 's/stream=True/stream=False/' /tmp/vibe/vibe/core/client.py
RUN git clone --branch v2.0.2 --depth 1 https://github.com/mistralai/mistral-vibe /tmp/vibe \
    && cat /tmp/system-prompt-suffix.md >> /tmp/vibe/vibe/core/prompts/cli.md \
    && /home/vibe/.local/bin/uv tool install /tmp/vibe \
    && rm -rf /tmp/vibe

# Create vibe config directory
RUN mkdir -p /home/vibe/.vibe

# Copy vibe configuration (will be added at build time)
COPY --chown=vibe:vibe config/vibe/vibe-config.toml /home/vibe/.vibe/config.toml
COPY --chown=vibe:vibe config/vibe/vibe-env /home/vibe/.vibe/.env
COPY --chown=vibe:vibe config/vibe/vibe-trusted-folders.toml /home/vibe/.vibe/trusted_folders.toml
COPY --chown=vibe:vibe config/vibe/agents /home/vibe/.vibe/agents
COPY --chown=vibe:vibe config/vibe/prompts /home/vibe/.vibe/prompts

# Copy secrets file and append to .env
# BUILD WILL FAIL if vibe-secrets.env doesn't exist - this is intentional!
# Copy vibe-secrets.env.example to vibe-secrets.env and fill in your API keys
COPY --chown=vibe:vibe config/vibe/vibe-secrets.env /tmp/vibe-secrets.env
RUN cat /tmp/vibe-secrets.env >> /home/vibe/.vibe/.env && rm /tmp/vibe-secrets.env

# ============================================================
# OPENCODE CLI (default coding agent, replaces Vibe as primary)
# ============================================================
# OpenCode is the community-driven MIT-licensed terminal coding agent.
# It connects to Ollama via the OpenAI-compatible API at 172.17.0.1:11434.
# Vibe CLI remains installed as a fallback — type "vibe" to use it.

# Install OpenCode CLI v1.1.53 (pinned for reproducible builds)
# https://github.com/anomalyco/opencode/releases/tag/v1.1.53
# sudo needed: npm global prefix is /usr/local, owned by root
RUN sudo npm install -g opencode-ai@1.1.53

# Pre-install ai-sdk-ollama provider (native Ollama API instead of OpenAI-compat layer)
# Pinned to v2.2.0: last version compatible with AI SDK v5 (OpenCode v1.1.53 uses ai@5.x)
# v3.x requires AI SDK v6 and is NOT compatible. OpenCode's dynamic installer always
# fetches @latest (which is v3.x), so we pre-install and use file:// in the config.
# ai-sdk-ollama uses the official 'ollama' npm client for native API access (/api/chat)
# instead of going through Ollama's OpenAI compatibility layer (/v1/chat/completions).
# RUN sudo npm install --prefix /opt/ai-providers ai-sdk-ollama@2.2.0
# @ai-sdk/mistral: Vercel AI SDK Mistral provider for Mistral Cloud API
# Pinned to v2.0.27: last major compatible with AI SDK v5 (v3.x requires AI SDK v6)
RUN sudo npm install --prefix /opt/ai-providers @ai-sdk/mistral@2.0.27

# Create OpenCode config directory
RUN mkdir -p /home/vibe/.config/opencode

# Copy OpenCode configuration (provider, model, air-gap settings)
# NOTE: Model ID must contain "devstral" (case-insensitive) to trigger OpenCode's
# Mistral-specific message normalization (transform.ts:87-131). This normalizes
# tool call IDs to 9-char alphanumeric (Mistral requirement) and inserts bridging
# "Done." messages between tool-result→user transitions. Without this, multi-turn
# tool calling will break with Devstral/Mistral models.
COPY --chown=vibe:vibe config/opencode/opencode.json /home/vibe/.config/opencode/opencode.json

# Copy OpenCode custom instructions (environment context for the agent)
COPY --chown=vibe:vibe config/opencode/opencode-agents.md /home/vibe/.config/opencode/AGENTS.md

# Runtime model toggle: "local" = Ollama, "cloud" = Mistral API
# Override at container start: docker run -e VIBE_MODE=cloud ...
ENV VIBE_MODE=local

# Air-gapped environment: disable all network fetches
ENV OPENCODE_DISABLE_MODELS_FETCH=true
ENV OPENCODE_DISABLE_AUTOUPDATE=true
ENV OPENCODE_DISABLE_LSP_DOWNLOAD=true

# Copy session startup script (for persistent tmux sessions)
COPY --chown=vibe:vibe config/start-session.sh /home/vibe/.local/bin/start-session.sh
RUN chmod +x /home/vibe/.local/bin/start-session.sh

# Copy container entrypoint (one-time setup: applies VIBE_MODE, then starts ttyd)
COPY --chown=vibe:vibe config/entrypoint.sh /home/vibe/.local/bin/entrypoint.sh
RUN chmod +x /home/vibe/.local/bin/entrypoint.sh

# Copy tmux configuration
COPY --chown=vibe:vibe config/tmux.conf /home/vibe/.tmux.conf

# Create workspace directory for user files
RUN mkdir -p /home/vibe/workspace

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
    && echo 'echo "- Type \"vibe --agent auto-approve\" to start Vibe CLI (default)"' >> /home/vibe/.bashrc \
    && echo 'echo "- Tip: Ask the agent to \"use subagents\" for deeper research"' >> /home/vibe/.bashrc \
    && echo 'echo "- Your workspace is /home/vibe/workspace"' >> /home/vibe/.bashrc \
    && echo 'echo "- Password for sudo: password"' >> /home/vibe/.bashrc \
    && echo 'echo ""' >> /home/vibe/.bashrc

WORKDIR /home/vibe/workspace

# Expose ttyd port
EXPOSE 7681

# Entrypoint: applies VIBE_MODE to Vibe CLI config, then starts ttyd
# See config/entrypoint.sh for ttyd flags and details
CMD ["/home/vibe/.local/bin/entrypoint.sh"]
