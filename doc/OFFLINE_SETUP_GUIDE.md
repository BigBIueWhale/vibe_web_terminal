# Offline Setup Guide

**You are on an ONLINE Linux machine collecting files. Later you will transfer everything to an OFFLINE Ubuntu 24.04 LTS Desktop machine with an NVIDIA GeForce RTX 5090 graphics card.**

---

## Part 1: Collecting Files (Online Machine)

---

### Step 1: Get the Debian Package Installer Tool

This tool downloads `.deb` packages WITH all their dependencies automatically.

```bash
cd ~
git clone https://github.com/MaSsTerKidd0/Debian-Package-Installer.git
cd Debian-Package-Installer
```

---

### Step 2: Download the Ubuntu Package Index

This downloads metadata so the tool knows what packages exist for Ubuntu 24.04 LTS.

```bash
python3 update_repository.py \
  --base-url https://archive.ubuntu.com/ubuntu/dists \
  --suites noble noble-updates noble-security \
  --components main restricted universe multiverse \
  --platform binary-amd64
```

Wait for it to finish. A `./repository/` folder will appear.

---

### Step 3: Download NVIDIA GeForce RTX 5090 Driver Packages

The NVIDIA GeForce RTX 5090 graphics card requires the open kernel module driver variant.

```bash
python3 debian-package-installer.py \
  --base-url https://archive.ubuntu.com/ubuntu \
  --packages \
    nvidia-driver-580-open \
    nvidia-dkms-580-open
```

Downloaded files go into `./downloaded/`.

---

### Step 4: Download Base System Packages

These are needed for: Python virtual environments, compiling Rust code, running Docker, and extracting Ollama.

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
    zstd
```

---

### Step 5: Download Docker Engine Packages

Docker Engine is not in Ubuntu's repository. Download from Docker's website:

```bash
mkdir -p ./downloaded/docker
cd ./downloaded/docker

wget https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/containerd.io_2.2.1-1_amd64.deb
wget "https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-ce-cli_5%3A29.2.1-1~ubuntu.24.04~noble_amd64.deb"
wget "https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-ce_5%3A29.2.1-1~ubuntu.24.04~noble_amd64.deb"
wget "https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-buildx-plugin_0.31.1-1~ubuntu.24.04~noble_amd64.deb"
wget "https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-compose-plugin_5.0.2-1~ubuntu.24.04~noble_amd64.deb"

cd ~/Debian-Package-Installer
```

---

### Step 6: Download NVIDIA Container Toolkit Packages

This lets Docker use the NVIDIA GeForce RTX 5090 GPU. Without it, `--gpus all` fails.

```bash
mkdir -p ./downloaded/nvidia-container
cd ./downloaded/nvidia-container

wget https://nvidia.github.io/libnvidia-container/stable/deb/amd64/libnvidia-container1_1.18.2-1_amd64.deb
wget https://nvidia.github.io/libnvidia-container/stable/deb/amd64/libnvidia-container-tools_1.18.2-1_amd64.deb
wget https://nvidia.github.io/libnvidia-container/stable/deb/amd64/nvidia-container-toolkit-base_1.18.2-1_amd64.deb
wget https://nvidia.github.io/libnvidia-container/stable/deb/amd64/nvidia-container-toolkit_1.18.2-1_amd64.deb

cd ~/Debian-Package-Installer
```

---

### Step 7: Download Ollama v0.15.4

Ollama runs Large Language Models on your NVIDIA GeForce RTX 5090 graphics card.

```bash
wget -P ./downloaded/ https://github.com/ollama/ollama/releases/download/v0.15.4/ollama-linux-amd64.tar.zst
```

File size: 1.66 GB. Format is `.tar.zst` which needs the `zstd` package to extract.

---

### Step 8: Download Ollama Models

Install Ollama temporarily on your online machine, pull models, then package them:

```bash
curl -fsSL https://ollama.com/install.sh | sh

ollama pull devstral
ollama pull qwen3:32b

tar -cvf ./downloaded/ollama-models.tar ~/.ollama/models/
```

Each model is 15-25 GB.

---

### Step 9: Clone and Prepare the Vibe Web Terminal Repository

```bash
git clone https://github.com/BigBIueWhale/vibe_web_terminal.git ~/vibe_web_terminal
```

Download Python packages for the server:

```bash
pip download -r ~/vibe_web_terminal/server/requirements.txt -d ./downloaded/pip-packages/
```

---

### Step 10: Handle Rust (Choose One Option)

**Option A: Pre-build the binary (recommended)**

Build on the online machine, transfer only the binary:

```bash
cd ~/vibe_web_terminal/rust_proxy
cargo build --release
```

Binary location: `~/vibe_web_terminal/rust_proxy/target/release/rust_proxy`

**Option B: Vendor dependencies for offline compilation**

```bash
cd ~/vibe_web_terminal/rust_proxy
cargo vendor

mkdir -p .cargo
cat > .cargo/config.toml << 'EOF'
[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "vendor"
EOF
```

Also download rustup:

```bash
wget -P ~/Debian-Package-Installer/downloaded/ https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init
```

---

### Step 11: Build and Export the Docker Image

```bash
cd ~/vibe_web_terminal
./setup.sh --force-build

docker save vibe-terminal:latest | gzip > ~/Debian-Package-Installer/downloaded/vibe-terminal-image.tar.gz
```

File size: approximately 8 GB.

---

### Step 12: Package Everything

```bash
cd ~/Debian-Package-Installer
tar -cvf offline-bundle.tar downloaded/
```

Transfer these to your offline machine:
- `offline-bundle.tar`
- `~/vibe_web_terminal/` folder

---

## Part 2: Installation (Offline Machine)

---

### Step A: Configure BIOS

1. Restart the computer
2. Press F2 or DEL during boot to enter BIOS/UEFI
3. Find **Secure Boot** and set it to **Disabled**
4. Save and exit

The NVIDIA GeForce RTX 5090 open kernel modules require Secure Boot to be disabled.

---

### Step B: Extract the Bundle

```bash
cd ~
tar -xvf offline-bundle.tar
```

---

### Step C: Install Base System Packages

```bash
cd ~/downloaded
sudo dpkg -i *.deb || true
sudo apt-get install -f
sudo dpkg -i *.deb
```

First run may show errors. That is normal. The `apt-get install -f` command fixes missing dependencies using packages from the Ubuntu installation media.

---

### Step D: Install NVIDIA GeForce RTX 5090 Driver

```bash
sudo dpkg -i nvidia-driver-580-open*.deb nvidia-dkms-580-open*.deb || true
sudo apt-get install -f
sudo reboot
```

After reboot, run:

```bash
nvidia-smi
```

You should see `NVIDIA GeForce RTX 5090` in the output.

---

### Step E: Install Docker Engine

```bash
cd ~/downloaded/docker
sudo dpkg -i containerd.io*.deb
sudo dpkg -i docker-ce-cli*.deb
sudo dpkg -i docker-ce_*.deb
sudo dpkg -i docker-buildx-plugin*.deb
sudo dpkg -i docker-compose-plugin*.deb

sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

---

### Step F: Install NVIDIA Container Toolkit

```bash
cd ~/downloaded/nvidia-container
sudo dpkg -i libnvidia-container1*.deb
sudo dpkg -i libnvidia-container-tools*.deb
sudo dpkg -i nvidia-container-toolkit-base*.deb
sudo dpkg -i nvidia-container-toolkit*.deb

sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Test it:

```bash
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
```

---

### Step G: Install Ollama

```bash
cd ~/downloaded
tar -xf ollama-linux-amd64.tar.zst
sudo cp bin/ollama /usr/local/bin/ollama
sudo chmod +x /usr/local/bin/ollama

sudo useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama
sudo usermod -a -G render,video ollama
```

Create the service file:

```bash
sudo tee /etc/systemd/system/ollama.service << 'EOF'
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
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KEEP_ALIVE=-1"

[Install]
WantedBy=multi-user.target
EOF
```

Start Ollama:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
```

Load the models:

```bash
sudo mkdir -p /usr/share/ollama/.ollama/
sudo tar -xvf ollama-models.tar -C /usr/share/ollama/.ollama/ --strip-components=2
sudo chown -R ollama:ollama /usr/share/ollama/.ollama/
sudo systemctl restart ollama
```

Test it:

```bash
curl http://localhost:11434/api/tags
```

---

### Step H: Set Up Vibe Web Terminal

```bash
docker load < ~/downloaded/vibe-terminal-image.tar.gz

cd ~/vibe_web_terminal
python3 -m venv venv
source venv/bin/activate
pip install --no-index --find-links=~/downloaded/pip-packages/ -r server/requirements.txt
```

If you pre-built the Rust binary (Option A), copy it to the correct location:

```bash
mkdir -p rust_proxy/target/release/
cp /path/to/rust_proxy rust_proxy/target/release/
```

If you vendored dependencies (Option B), build now:

```bash
chmod +x ~/downloaded/rustup-init
~/downloaded/rustup-init -y
source ~/.cargo/env
cd rust_proxy
cargo build --release --offline
cd ..
```

Start:

```bash
./run.sh
```

Open https://localhost:8443 in your browser.

---

## Verification Checklist

Run these commands to confirm everything works:

```bash
nvidia-smi
```
Shows: NVIDIA GeForce RTX 5090

```bash
docker --version
```
Shows: Docker version number

```bash
curl http://localhost:11434/api/tags
```
Shows: List of Ollama models

```bash
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
```
Shows: NVIDIA GeForce RTX 5090 inside Docker container

---

## File Sizes

| File | Size |
|------|------|
| Ubuntu .deb packages | ~500 MB |
| Docker Engine .deb packages | ~150 MB |
| NVIDIA Container Toolkit .deb packages | ~50 MB |
| Ollama v0.15.4 | 1.7 GB |
| Python packages | ~100 MB |
| Rust binary | ~10 MB |
| Docker image (vibe-terminal) | ~8 GB |
| LLM Models | 20-50 GB |
| **Total** | **~30-60 GB** |
