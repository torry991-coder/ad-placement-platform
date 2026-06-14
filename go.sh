#!/usr/bin/env bash
# 智能广告投放系统 · 阿里云一键部署
# ssh 后执行: bash go.sh
set -e

echo ">>> 解压项目..."
cd /root && tar -xzf ad-platform.tar.gz 2>/dev/null

echo ">>> 构建前端..."
cd /root/frontend && npm run build 2>/dev/null && cd /root

echo ">>> 写 Nginx 配置..."
python3.11 -c "
c='''server {
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
        proxy_set_header Connection upgrade;
    }
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}'''
with open('/etc/nginx/conf.d/ad-platform.conf','w') as f: f.write(c)
"

echo ">>> 启动服务..."
systemctl restart nginx 2>/dev/null
kill $(lsof -ti:8000) 2>/dev/null || true
nohup python3.11 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
sleep 2

echo ">>> 验证..."
curl -s http://127.0.0.1:8000/api/health
echo ""
echo "==================================="
echo "  打开 http://$(curl -s ifconfig.me)"
echo "==================================="
