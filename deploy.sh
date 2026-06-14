#!/usr/bin/env bash
# ============================================================
#  Ad Placement Platform · Alibaba Cloud 一键部署
#  用法: ssh 到服务器后 bash deploy.sh
# ============================================================
set -e

echo "=== 1. 安装 Python 3.11 ==="
yum install -y python3.11 python3.11-pip python3.11-devel 2>/dev/null || true

echo "=== 2. 安装 Node.js ==="
if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
    yum install -y nodejs
fi

echo "=== 3. 安装 Nginx ==="
yum install -y nginx 2>/dev/null || true

echo "=== 4. 安装 Python 依赖 ==="
python3.11 -m pip install --upgrade pip --quiet
python3.11 -m pip install -r backend/requirements.txt --quiet

echo "=== 5. 构建前端 ==="
cd frontend && npm install --silent && npm run build && cd ..

echo "=== 6. 配置 Nginx ==="
python3.11 -c "
conf = '''server {
    listen 80;
    server_name _;
    root /root/frontend/dist;
    index index.html;
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \"upgrade\";
    }
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}'''
with open('/etc/nginx/conf.d/ad-platform.conf', 'w') as f:
    f.write(conf)
"

echo "=== 7. 配置后端服务 ==="
python3.11 -c "
unit = '''[Unit]
Description=Ad Platform Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root
ExecStart=/usr/bin/python3.11 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
'''
with open('/etc/systemd/system/ad-platform-backend.service', 'w') as f:
    f.write(unit)
"

echo "=== 8. 启动 ==="
systemctl daemon-reload
systemctl enable ad-platform-backend nginx 2>/dev/null || true
systemctl restart ad-platform-backend
systemctl restart nginx

echo ""
echo "============================================"
echo "  DONE! Open: http://$(curl -s ifconfig.me)"
echo "  Login: admin / admin123"
echo "============================================"
