#!/usr/bin/env bash
# ==============================================================================
# 🚀 1-CLICK VPS DEPLOYMENT SCRIPT: CYBERSHORTS AI AUTOMATION
# Supports: Ubuntu 20.04 / 22.04 / 24.04 LTS & Debian 11 / 12
# ==============================================================================

set -e

echo "======================================================================"
echo "⚡ Starting Automated VPS Installation for CyberShorts AI"
echo "======================================================================"

# 1. Update system packages
echo "[*] Updating package repositories..."
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
    curl \
    git \
    ffmpeg \
    python3 \
    python3-pip \
    python3-venv \
    fonts-roboto \
    fonts-freefont-ttf \
    ca-certificates

# 2. Setup Python virtual environment
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

echo "[*] Setting up Python virtual environment in $APP_DIR/.venv ..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 3. Create .env from template if missing
if [ ! -f ".env" ]; then
    echo "[*] Creating default .env file..."
    cp .env.example .env
fi

# 4. Setup systemd background daemon service
SERVICE_NAME="ai-video"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

echo "[*] Configuring systemd background service at $SERVICE_PATH..."
sudo bash -c "cat << 'EOF' > $SERVICE_PATH
[Unit]
Description=CyberShorts AI - Autonomous Video Production Daemon
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$APP_DIR/.venv/bin/python run.py --daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}

echo "======================================================================"
echo "✅ VPS DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "======================================================================"
echo "1. Service is running 24/7 in the background: sudo systemctl status ${SERVICE_NAME}"
echo "2. View live logs: sudo journalctl -u ${SERVICE_NAME} -f"
echo "3. Web Mission Control: http://$(curl -s ifconfig.me):8000"
echo "======================================================================"

