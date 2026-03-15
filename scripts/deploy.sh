#!/bin/bash
# Deploy the Peptide Compare Bot as a systemd service on the VPS.
# Run once to set up, then use: systemctl restart peptide-bot

set -euo pipefail

BOT_DIR="/root/peptide-price-bot"
SERVICE_NAME="peptide-bot"

echo "Setting up ${SERVICE_NAME}..."

# Create systemd service
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Peptide Compare Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=${BOT_DIR}
ExecStart=${BOT_DIR}/venv/bin/python -m bot.main
Restart=always
RestartSec=10
EnvironmentFile=${BOT_DIR}/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

echo "Done. Check status with: systemctl status ${SERVICE_NAME}"
echo "View logs with: journalctl -u ${SERVICE_NAME} -f"
