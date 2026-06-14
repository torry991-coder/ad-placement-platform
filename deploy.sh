#!/usr/bin/env bash
# ============================================================
#  智能广告投放系统 · 阿里云一键部署脚本
#  在阿里云 Ubuntu 22.04 服务器上运行此脚本即可
#
#  用法: chmod +x deploy.sh && sudo ./deploy.sh
# ============================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║   智能广告投放系统 · 一键部署       ║"
echo "  ║   Ad Placement Platform Deployer    ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

APP_DIR="/opt/ad-platform"
PYTHON=$(which python3.11 2>/dev/null || which python3)

# ── Step 1: Install system dependencies ─────────────────────────────
echo -e "${YELLOW}[1/6] Installing system dependencies...${NC}"
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx git curl

# ── Step 2: Create app directory ────────────────────────────────────
echo -e "${YELLOW}[2/6] Setting up application directory...${NC}"
mkdir -p $APP_DIR
cd $APP_DIR

if [ ! -d ".git" ]; then
    git clone --depth 1 https://github.com/torry991-coder/ad-placement-platform.git .
fi

# ── Step 3: Install Python dependencies ─────────────────────────────
echo -e "${YELLOW}[3/6] Installing Python dependencies...${NC}"
pip3 install -r backend/requirements.txt

# ── Step 4: Build frontend ──────────────────────────────────────────
echo -e "${YELLOW}[4/6] Building frontend...${NC}"
apt-get install -y -qq nodejs npm 2>/dev/null || {
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
}
cd frontend
npm install --silent
npm run build
cd ..

# ── Step 5: Configure systemd services ───────────────────────────────
echo -e "${YELLOW}[5/6] Configuring services...${NC}"

# Backend systemd service
cat > /etc/systemd/system/ad-platform-backend.service << 'EOF'
[Unit]
Description=Ad Platform Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ad-platform
ExecStart=/usr/bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Nginx config
cat > /etc/nginx/sites-available/ad-platform << 'EOF'
server {
    listen 80;
    server_name _;

    # Frontend static files
    root /opt/ad-platform/frontend/dist;
    index index.html;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket proxy
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

ln -sf /etc/nginx/sites-available/ad-platform /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# ── Step 6: Start services ──────────────────────────────────────────
echo -e "${YELLOW}[6/6] Starting services...${NC}"
systemctl daemon-reload
systemctl enable ad-platform-backend
systemctl restart ad-platform-backend
systemctl restart nginx

# ── Done ────────────────────────────────────────────────────────────
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗"
echo -e "║  ✅ 部署完成！                              ║"
echo -e "╠══════════════════════════════════════════════╣"
echo -e "║  网站地址: http://${SERVER_IP}                ║"
echo -e "║  API文档:  http://${SERVER_IP}/api/docs       ║"
echo -e "║  数据大屏: http://${SERVER_IP}/bigscreen      ║"
echo -e "╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "默认登录: ${YELLOW}admin / admin123${NC}"
echo ""
echo -e "常用命令:"
echo -e "  查看状态: ${YELLOW}systemctl status ad-platform-backend nginx${NC}"
echo -e "  查看日志: ${YELLOW}journalctl -u ad-platform-backend -f${NC}"
echo -e "  重启服务: ${YELLOW}systemctl restart ad-platform-backend${NC}"
echo ""
