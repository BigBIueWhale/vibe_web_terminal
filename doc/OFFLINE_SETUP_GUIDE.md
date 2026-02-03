# Offline Setup Guide for Vibe Web Terminal

**Target Environment:** Ubuntu 24.04 LTS Desktop (Wayland) with NVIDIA GeForce RTX 5090 Graphics Card

---

## Important Clarification

**Everything inside the Docker container is NOT a problem.** You build the Docker image once while online, export it, and import it on the offline machine. The container includes all Python packages, Node.js packages, language runtimes, fonts, browsers, and tools.

**This guide focuses ONLY on host system requirements** — software that must be installed on your Ubuntu 24.04 LTS Desktop machine itself, outside the container.

---

## Table of Contents

1. [What Ubuntu 24.04 LTS Desktop Already Includes](#1-what-ubuntu-2404-lts-desktop-already-includes)
2. [BIOS/UEFI Configuration](#2-biosuefi-configuration)
3. [NVIDIA GeForce RTX 5090 Driver and CUDA Toolkit](#3-nvidia-geforce-rtx-5090-driver-and-cuda-toolkit)
4. [Docker Engine](#4-docker-engine)
5. [NVIDIA Container Toolkit](#5-nvidia-container-toolkit)
6. [Ollama](#6-ollama)
7. [Host Python Packages](#7-host-python-packages)
8. [Rust Toolchain](#8-rust-toolchain)
9. [Pre-Built Docker Image](#9-pre-built-docker-image)
10. [LLM Models for Ollama](#10-llm-models-for-ollama)
11. [Complete Offline Package Download Scripts](#11-complete-offline-package-download-scripts)
12. [Installation Order on Offline Machine](#12-installation-order-on-offline-machine)

---

## 1. What Ubuntu 24.04 LTS Desktop Already Includes

These components come **pre-installed** with the Ubuntu 24.04 LTS Desktop ISO image and do **NOT** need to be downloaded:

| Component | Version | Notes |
|-----------|---------|-------|
| Linux Kernel | 6.8.0 | Sufficient for NVIDIA driver 580.x |
| Python | 3.12 | Interpreter only, no pip/venv |
| Git | 2.43+ | Pre-installed |
| systemd | 255.4 | Service management |
| GNU C Library (glibc) | 2.39 | Core system library |
| GNOME Desktop | 46 | With Wayland session |
| Firefox | Snap | Web browser |
| Nautilus | - | File manager |

### What Ubuntu 24.04 LTS Desktop Does NOT Include

These must be downloaded and installed:

| Component | Why Needed |
|-----------|------------|
| `python3-pip` | Install Python packages |
| `python3-venv` | Create virtual environments |
| `build-essential` | Compile NVIDIA driver kernel modules and Rust proxy |
| `pkg-config` | Required for Rust compilation |
| `libssl-dev` | Required for Rust TLS support |
| `nvidia-driver-580-open` | GPU driver for NVIDIA GeForce RTX 5090 |
| `nvidia-dkms-580-open` | DKMS kernel module for NVIDIA driver |
| `cuda-toolkit-13-0` | CUDA 13.0 development toolkit |
| Docker Engine | Run containers |
| NVIDIA Container Toolkit | GPU passthrough to Docker |
| Ollama | Run local LLM models |
| Rust/Cargo | Build the reverse proxy |

---

## 2. BIOS/UEFI Configuration

Before installing Ubuntu or the NVIDIA drivers, configure your BIOS/UEFI:

| Setting | Required Value | Notes |
|---------|----------------|-------|
| **Secure Boot** | **Disabled** | NVIDIA open kernel modules require Secure Boot to be disabled |
| Fast Boot | Disabled (optional) | Helps with troubleshooting |
| Auto Boot after Power Loss | Enabled (optional) | Useful for servers |

---

## 3. NVIDIA GeForce RTX 5090 Driver and CUDA Toolkit

The NVIDIA GeForce RTX 5090 uses the Blackwell architecture. Installation is done via **apt packages**, not `.run` files.

### Driver Packages (from Ubuntu Repository)

The NVIDIA GeForce RTX 5090 requires the **open kernel module** driver variant. These packages are available in Ubuntu 24.04 LTS repositories:

| Package | Purpose |
|---------|---------|
| `nvidia-driver-580-open` | NVIDIA driver 580 with open kernel modules |
| `nvidia-dkms-580-open` | DKMS kernel module for automatic rebuilding on kernel updates |

### Online Installation (for reference)

```bash
sudo apt update
sudo apt install -y nvidia-driver-580-open nvidia-dkms-580-open
sudo reboot
```

After reboot, verify with:
```bash
nvidia-smi
```

You should see the NVIDIA GeForce RTX 5090 listed.

### CUDA Toolkit 13.0 (from NVIDIA Repository)

CUDA Toolkit is installed from NVIDIA's official apt repository.

**Online installation (for reference):**

```bash
# Add NVIDIA CUDA repository
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update

# Install CUDA Toolkit 13.0
sudo apt install -y cuda-toolkit-13-0
```

**Add CUDA to your PATH:**

```bash
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

**Verify CUDA installation:**

```bash
nvcc -V
```

### Wayland Compatibility

The NVIDIA 580.x driver series supports Wayland through the GBM backend. Ubuntu 24.04 LTS Desktop with GNOME 46 on Wayland will work correctly with this driver.

**Note:** When using Wayland with remote desktop software (RustDesk, TeamViewer), you may need an EDID DisplayPort emulator dongle if the physical display is disconnected. Without it, the remote desktop may show a black screen.

---

## 4. Docker Engine

Docker Engine is NOT included in Ubuntu 24.04 LTS Desktop and must be installed from Docker's official repository.

### Current Version

| Package | Version | Notes |
|---------|---------|-------|
| `docker-ce` | 5:29.2.1-1~ubuntu.24.04~noble | Docker Engine |
| `docker-ce-cli` | 5:29.2.1-1~ubuntu.24.04~noble | Command-line interface |
| `containerd.io` | 2.2.1-1 | Container runtime |
| `docker-buildx-plugin` | 0.31.1-1~ubuntu.24.04~noble | Build extension |
| `docker-compose-plugin` | 5.0.2-1~ubuntu.24.04~noble | Compose V2 |

### Download Location

**Repository index:** [https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/](https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/)

### Required .deb Files

Download these specific files:

1. `containerd.io_2.2.1-1_amd64.deb`
2. `docker-ce-cli_5%3A29.2.1-1~ubuntu.24.04~noble_amd64.deb`
3. `docker-ce_5%3A29.2.1-1~ubuntu.24.04~noble_amd64.deb`
4. `docker-buildx-plugin_0.31.1-1~ubuntu.24.04~noble_amd64.deb`
5. `docker-compose-plugin_5.0.2-1~ubuntu.24.04~noble_amd64.deb`

### Dependencies from Ubuntu Repository

Docker packages require these dependencies from the Ubuntu archive (use the Debian Package Installer tool to download them with all transitive dependencies):

```
iptables
libip4tc2
libip6tc2
libnetfilter-conntrack3
libnfnetlink0
```

---

## 5. NVIDIA Container Toolkit

Required for Docker containers to access the NVIDIA GeForce RTX 5090 GPU. This enables the `--gpus all` flag in Docker.

### Current Version

| Package | Version |
|---------|---------|
| `nvidia-container-toolkit` | 1.18.2-1 |
| `nvidia-container-toolkit-base` | 1.18.2-1 |
| `libnvidia-container1` | 1.18.2-1 |
| `libnvidia-container-tools` | 1.18.2-1 |

### Online Installation (for reference)

```bash
# Add NVIDIA Container Toolkit repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Verification

```bash
# Test GPU access in Docker
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
```

You should see your NVIDIA GeForce RTX 5090 listed in the container.

### Offline Download

Download these .deb files from NVIDIA's repository:

**Base URL:** `https://nvidia.github.io/libnvidia-container/stable/deb/amd64/`

1. `libnvidia-container1_1.18.2-1_amd64.deb`
2. `libnvidia-container-tools_1.18.2-1_amd64.deb`
3. `nvidia-container-toolkit-base_1.18.2-1_amd64.deb`
4. `nvidia-container-toolkit_1.18.2-1_amd64.deb`

---

## 6. Ollama

Ollama runs LLM models locally and provides an OpenAI-compatible API.

### Current Version

| Version | Release Date | File Size |
|---------|--------------|-----------|
| **v0.15.4** | February 1, 2026 | 1.66 GB |

### Download Link

**Stable release (v0.15.4):**
```
https://github.com/ollama/ollama/releases/download/v0.15.4/ollama-linux-amd64.tar.zst
```

**SHA256 checksum:**
```
464e3de993cfc9854b91c9d9a067341b840a78920e2688903a3d0ea55e7c61c8
```

### Key Features in v0.15.4

- Automatic context window sizing based on VRAM:
  - NVIDIA GeForce RTX 5090 (32GB VRAM): Defaults to **32,768 context**
- Experimental agent loop (`ollama run --experimental`)
- Anthropic API compatibility (`/v1/messages` endpoint)
- DeepSeek-V3.1 tool parsing support

### Installation Method

```bash
# Extract the archive (requires zstd)
tar -xf ollama-linux-amd64.tar.zst

# Install the binary
sudo cp bin/ollama /usr/local/bin/ollama
sudo chmod +x /usr/local/bin/ollama

# Create the ollama user
sudo useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama
sudo usermod -a -G render,video ollama
```

### Ollama systemd Service File

Save as `/etc/systemd/system/ollama.service`:

```ini
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=/usr/share/ollama/.ollama/models"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KEEP_ALIVE=-1"

[Install]
WantedBy=multi-user.target
```

**Important environment variables:**

| Variable | Value | Purpose |
|----------|-------|---------|
| `OLLAMA_HOST` | `0.0.0.0:11434` | Listen on all interfaces (or `127.0.0.1:11434` for localhost only) |
| `OLLAMA_FLASH_ATTENTION` | `1` | Enable Flash Attention for better NVIDIA GPU performance |
| `OLLAMA_KEEP_ALIVE` | `-1` | Keep models loaded in VRAM forever (instead of default 5 minutes) |
| `OLLAMA_NUM_PARALLEL` | `1` | Number of parallel requests (set to 1 if VRAM is limited) |

---

## 7. Host Python Packages

The host system needs Python packages only for running the FastAPI server (NOT for the container).

### Required Ubuntu Packages

```
python3-pip
python3-venv
```

### Python Package List (server/requirements.txt)

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.128.0 | Web framework |
| uvicorn[standard] | 0.40.0 | ASGI server |
| python-multipart | 0.0.22 | File uploads |
| aiodocker | 0.25.0 | Docker API client |
| websockets | 16.0 | WebSocket support |
| httpx | 0.28.1 | HTTP client |
| aiofiles | 25.1.0 | Async file I/O |
| jinja2 | 3.1.6 | HTML templating |
| py7zr | 1.1.2 | 7z compression |
| bcrypt | 5.0.0 | Password hashing |
| pyyaml | 6.0.2 | YAML parsing |

### Offline Download Method

```bash
# On online machine with same architecture (x86_64)
pip download -r server/requirements.txt -d ./offline-pip-packages/
```

This downloads all wheel files including transitive dependencies.

---

## 8. Rust Toolchain

Required to build the high-performance reverse proxy (`rust_proxy`).

### Current Version

| Component | Version |
|-----------|---------|
| rustup | Latest |
| Rust stable | 1.85.x |
| Cargo | 1.85.x |

### Download Link

**rustup-init for Linux x86_64:**
```
https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init
```

### Required Ubuntu Packages for Rust Compilation

```
build-essential
pkg-config
libssl-dev
```

### Offline Rust Setup with Vendored Dependencies

**Step 1: On online machine, vendor the dependencies:**

```bash
cd vibe_web_terminal/rust_proxy
cargo vendor
```

This creates a `vendor/` directory with all crates.

**Step 2: Create `.cargo/config.toml`:**

```toml
[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "vendor"
```

**Step 3: Build offline:**

```bash
cargo build --release --offline
```

### Alternative: Pre-build the Binary

Instead of vendoring, you can build the binary on an online machine and transfer just the binary:

```bash
# On online machine
cd rust_proxy
cargo build --release

# Transfer this file to offline machine:
# rust_proxy/target/release/rust_proxy
```

---

## 9. Pre-Built Docker Image

The Docker image contains everything needed inside the container. Build it once online, then transfer.

### Build and Export

```bash
# On online machine with internet access
cd vibe_web_terminal
./setup.sh --force-build

# Export the image (approximately 8 GB compressed)
docker save vibe-terminal:latest | gzip > vibe-terminal-image.tar.gz
```

### Import on Offline Machine

```bash
docker load < vibe-terminal-image.tar.gz
docker images | grep vibe-terminal
```

---

## 10. LLM Models for Ollama

### Recommended Models for NVIDIA GeForce RTX 5090 (32 GB VRAM)

| Model | Parameters | VRAM Usage | Speed | Best For |
|-------|------------|------------|-------|----------|
| devstral | 24B | ~16 GB | ~80 tok/s | Coding |
| codestral | 22B | ~14 GB | ~90 tok/s | Coding |
| qwen3:32b | 32B | ~20 GB | ~60 tok/s | General |
| gemma3:27b | 27B | ~17 GB | ~76 tok/s | General |
| gpt-oss:120b | 120B | ~65 GB | N/A | Too large for single RTX 5090 |

### Pre-download Models

```bash
# On online machine with Ollama installed
ollama pull devstral
ollama pull codestral
ollama pull qwen3:32b
ollama pull gemma3:27b

# Find model location
ls ~/.ollama/models/

# Package for transfer (may be 20-50 GB total)
tar -cvf ollama-models.tar ~/.ollama/models/
```

### Transfer to Offline Machine

```bash
# On offline machine
sudo mkdir -p /usr/share/ollama/.ollama/
sudo tar -xvf ollama-models.tar -C /usr/share/ollama/.ollama/ --strip-components=2
sudo chown -R ollama:ollama /usr/share/ollama/.ollama/
```

---

## 11. Complete Offline Package Download Scripts

### Using the Debian Package Installer Tool

Clone the tool: [https://github.com/MaSsTerKidd0/Debian-Package-Installer](https://github.com/MaSsTerKidd0/Debian-Package-Installer)

```bash
git clone https://github.com/MaSsTerKidd0/Debian-Package-Installer.git
cd Debian-Package-Installer
```

### Step 1: Update Repository Index for Ubuntu 24.04 LTS (Noble Numbat)

```bash
# Ubuntu main repositories
python3 update_repository.py \
  --base-url https://archive.ubuntu.com/ubuntu/dists \
  --suites noble noble-updates noble-security \
  --components main restricted universe multiverse \
  --platform binary-amd64
```

### Step 2: Download NVIDIA Driver and CUDA Packages

First, add the NVIDIA CUDA repository to the index:

```bash
# Download the CUDA keyring package directly
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb

# Add NVIDIA CUDA repository to the Debian Package Installer
python3 update_repository.py \
  --base-url https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/dists \
  --suites / \
  --components / \
  --platform binary-amd64
```

Then download the NVIDIA packages:

```bash
python3 debian-package-installer.py \
  --base-url https://archive.ubuntu.com/ubuntu,https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64 \
  --packages \
    nvidia-driver-580-open \
    nvidia-dkms-580-open \
    cuda-toolkit-13-0
```

### Step 3: Download Base System Packages

```bash
python3 debian-package-installer.py \
  --base-url https://archive.ubuntu.com/ubuntu \
  --packages \
    python3-pip \
    python3-venv \
    build-essential \
    pkg-config \
    libssl-dev \
    linux-headers-generic \
    dkms \
    iptables \
    libip4tc2 \
    libip6tc2 \
    libnetfilter-conntrack3 \
    libnfnetlink0 \
    zstd
```

All `.deb` files will be in the `./downloaded/` directory.

### Step 4: Download Docker Packages

```bash
# Download directly from Docker's repository
wget https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/containerd.io_2.2.1-1_amd64.deb
wget "https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-ce-cli_5%3A29.2.1-1~ubuntu.24.04~noble_amd64.deb"
wget "https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-ce_5%3A29.2.1-1~ubuntu.24.04~noble_amd64.deb"
wget "https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-buildx-plugin_0.31.1-1~ubuntu.24.04~noble_amd64.deb"
wget "https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-compose-plugin_5.0.2-1~ubuntu.24.04~noble_amd64.deb"
```

### Step 5: Download NVIDIA Container Toolkit Packages

```bash
wget https://nvidia.github.io/libnvidia-container/stable/deb/amd64/libnvidia-container1_1.18.2-1_amd64.deb
wget https://nvidia.github.io/libnvidia-container/stable/deb/amd64/libnvidia-container-tools_1.18.2-1_amd64.deb
wget https://nvidia.github.io/libnvidia-container/stable/deb/amd64/nvidia-container-toolkit-base_1.18.2-1_amd64.deb
wget https://nvidia.github.io/libnvidia-container/stable/deb/amd64/nvidia-container-toolkit_1.18.2-1_amd64.deb
```

### Step 6: Download Python Packages

```bash
pip download -r server/requirements.txt -d ./offline-pip-packages/
```

### Step 7: Download Remaining Components

```bash
# Ollama v0.15.4
wget https://github.com/ollama/ollama/releases/download/v0.15.4/ollama-linux-amd64.tar.zst

# Rustup
wget https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init
```

---

## 12. Installation Order on Offline Machine

Execute in this exact order:

### Phase 1: BIOS Configuration

1. Enter BIOS/UEFI setup
2. **Disable Secure Boot**
3. Disable Fast Boot (optional)
4. Save and reboot into Ubuntu

### Phase 2: Base System Packages

```bash
# Install Ubuntu packages (from ./downloaded/)
cd downloaded
sudo dpkg -i *.deb || true  # Some may fail due to ordering
sudo apt-get install -f     # Fix dependencies from ISO
sudo dpkg -i *.deb          # Retry installation
```

### Phase 3: NVIDIA GeForce RTX 5090 Driver

```bash
# Install NVIDIA driver packages
sudo dpkg -i nvidia-driver-580-open*.deb nvidia-dkms-580-open*.deb || true
sudo apt-get install -f

# Reboot to load the driver
sudo reboot
```

After reboot:

```bash
# Verify NVIDIA driver
nvidia-smi
```

You should see:
```
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 580.x.xx    Driver Version: 580.x.xx    CUDA Version: 13.0                  |
|--------------------------------------------+------------------------+------------------+
| GPU  Name                 Persistence-M    | Bus-Id          Disp.A | Volatile Uncorr. ECC |
|                                            |                        |              |
|   0  NVIDIA GeForce RTX 5090          Off  | 00000000:01:00.0  On   |          N/A |
+--------------------------------------------+------------------------+------------------+
```

### Phase 4: CUDA Toolkit 13.0 (Optional)

Only needed if you want to compile CUDA programs on the host:

```bash
# Install CUDA keyring first
sudo dpkg -i cuda-keyring_1.1-1_all.deb

# Install CUDA Toolkit
sudo dpkg -i cuda-toolkit-13-0*.deb || true
sudo apt-get install -f

# Add to PATH
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# Verify
nvcc -V
```

### Phase 5: Docker Engine

```bash
# Install Docker packages (in order)
sudo dpkg -i containerd.io_2.2.1-1_amd64.deb
sudo dpkg -i docker-ce-cli_*.deb
sudo dpkg -i docker-ce_*.deb
sudo dpkg -i docker-buildx-plugin_*.deb
sudo dpkg -i docker-compose-plugin_*.deb

# Start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
```

### Phase 6: NVIDIA Container Toolkit

```bash
# Install packages (in order)
sudo dpkg -i libnvidia-container1_1.18.2-1_amd64.deb
sudo dpkg -i libnvidia-container-tools_1.18.2-1_amd64.deb
sudo dpkg -i nvidia-container-toolkit-base_1.18.2-1_amd64.deb
sudo dpkg -i nvidia-container-toolkit_1.18.2-1_amd64.deb

# Configure Docker runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify GPU access in Docker
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
```

### Phase 7: Ollama

```bash
# Extract and install (requires zstd, included in base packages)
tar -xf ollama-linux-amd64.tar.zst
sudo cp bin/ollama /usr/local/bin/ollama
sudo chmod +x /usr/local/bin/ollama

# Create user
sudo useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama
sudo usermod -a -G render,video ollama

# Create systemd service file (see Section 6 for contents)
sudo nano /etc/systemd/system/ollama.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama

# Load pre-downloaded models
sudo mkdir -p /usr/share/ollama/.ollama/
sudo tar -xvf ollama-models.tar -C /usr/share/ollama/.ollama/ --strip-components=2
sudo chown -R ollama:ollama /usr/share/ollama/.ollama/
sudo systemctl restart ollama

# Verify
curl http://localhost:11434/api/tags
```

### Phase 8: Vibe Web Terminal Setup

```bash
# Load Docker image
docker load < vibe-terminal-image.tar.gz

# Install Python packages
cd vibe_web_terminal
python3 -m venv venv
source venv/bin/activate
pip install --no-index --find-links=../offline-pip-packages/ -r server/requirements.txt

# Install Rust (if binary not pre-built)
chmod +x rustup-init
./rustup-init -y
source ~/.cargo/env

# Build proxy (if binary not pre-built)
cd rust_proxy
cargo build --release --offline
cd ..

# Run
./run.sh
```

### Phase 9: Verification

```bash
# Check all services
nvidia-smi                                    # GPU visible
docker --version                              # Docker running
curl http://localhost:11434/api/tags          # Ollama responding
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi  # GPU in Docker

# Start Vibe Web Terminal
./run.sh

# Access at https://localhost:8443
```

---

## Summary: Files to Transfer

| Item | Size (Approx.) | Source |
|------|----------------|--------|
| Ubuntu .deb packages (including NVIDIA driver) | ~500 MB | Debian Package Installer + Ubuntu repos |
| CUDA Toolkit 13.0 .deb packages | ~3 GB | NVIDIA CUDA repo |
| Docker .deb packages | ~150 MB | download.docker.com |
| NVIDIA Container Toolkit .deb | ~50 MB | nvidia.github.io |
| Ollama v0.15.4 | 1.7 GB | github.com/ollama |
| Python wheel packages | ~100 MB | pip download |
| Rust vendored crates (or pre-built binary) | ~300 MB / ~10 MB | cargo vendor |
| Docker image (vibe-terminal) | ~8 GB | docker save |
| LLM Models | 20-50 GB | ollama pull |
| **TOTAL** | **~35-65 GB** | |

---

## Sources

- [Personal Server Setup Guide - BigBIueWhale](https://github.com/BigBIueWhale/personal_server) — Working steps for NVIDIA GeForce RTX 5090 on Ubuntu 24.04 LTS
- [Docker Engine Install on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [NVIDIA Container Toolkit Installation Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- [Ollama GitHub Releases](https://github.com/ollama/ollama/releases)
- [Ollama GPU Hardware Support](https://docs.ollama.com/gpu)
- [Debian Package Installer Tool](https://github.com/MaSsTerKidd0/Debian-Package-Installer)
- [Ubuntu 24.04 LTS Deep Dive](https://ubuntu.com/blog/ubuntu-desktop-24-04-noble-numbat-deep-dive)
- [Cargo Vendor for Offline Builds](https://leichen.dev/rust/tool/2023/08/17/cargo-vendor.html)
- [NVIDIA CUDA Repository for Ubuntu 24.04](https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/)
