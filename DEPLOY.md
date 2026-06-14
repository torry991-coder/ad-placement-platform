# 🚀 阿里云部署指南

> 30 分钟将项目部署到公网，任何人可通过浏览器访问。

---

## 第一步：购买服务器

### 1. 打开购买页面

👉 **[阿里云轻量应用服务器 38元/年](https://www.aliyun.com/daily-act/ecs/activity_selection)**

找「轻量应用服务器」卡片。

### 2. 选择配置

| 选项 | 填什么 |
|------|--------|
| 地域 | 离你最近的（如杭州/上海） |
| 镜像 | **Ubuntu 22.04** |
| 套餐 | 2核 2G · 40G SSD · 200M 峰值 |

### 3. 购买

点「立即购买」→ 支付 **38元**。

---

## 第二步：配置安全组

买完后进入控制台，放行端口：

| 端口 | 用途 |
|------|------|
| **80** | HTTP（网页访问） |
| **443** | HTTPS（可选） |
| **22** | SSH（远程连接） |

路径：控制台 → 轻量应用服务器 → 你的服务器 → 防火墙 → 添加规则。

---

## 第三步：连接到服务器

**Windows:** 打开 PowerShell 或 Git Bash：

```bash
ssh root@你的公网IP
```

首次连接输入 `yes`，密码在阿里云控制台（或短信里）。

---

## 第四步：一键部署

连上服务器后，复制粘贴：

```bash
curl -fsSL https://raw.githubusercontent.com/torry991-coder/ad-placement-platform/main/deploy.sh | bash
```

脚本自动完成：
- 安装 Python + Node.js + Nginx
- 克隆项目代码
- 安装依赖 + 构建前端
- 配置 systemd（崩溃自动重启）
- 配置 Nginx 反向代理
- 启动所有服务

⏱️ 约 3-5 分钟。

---

## 第五步：打开浏览器

部署完成后，访问：

```
http://你的公网IP
```

你会看到登录页面。默认账号：

```
用户名: admin
密码:   admin123
```

---

## 目录

| 地址 | 内容 |
|------|------|
| `http://你的IP/` | 前端仪表盘 |
| `http://你的IP/bigscreen` | 数据大屏 |
| `http://你的IP/api/docs` | Swagger API 文档 |
| `http://你的IP/api/metrics` | Prometheus 指标 |
| `http://你的IP/api/health` | 健康检查 |

---

## 可选：绑域名

1. 去阿里云域名控制台买一个域名
2. 解析 A 记录到你的服务器 IP
3. 重新执行部署脚本（会自动适配）

---

## 可选：开启 HTTPS

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx
```

按照提示输入邮箱，选择域名，自动获得免费 SSL 证书。

---

## 常用命令

```bash
# 查看服务状态
systemctl status ad-platform-backend nginx

# 查看后端日志
journalctl -u ad-platform-backend -f

# 重启后端
systemctl restart ad-platform-backend

# 更新代码
cd /opt/ad-platform
git pull
systemctl restart ad-platform-backend
```

---

## 故障排查

| 问题 | 解决 |
|------|------|
| 网页打不开 | 检查安全组是否放行了 80 端口 |
| 后端 502 错误 | `systemctl status ad-platform-backend` 查看日志 |
| 端口被占用 | `lsof -i :8000` 查看是谁占用了端口 |
