# 生产环境部署指南

## 目录

1. [概述](#概述)
2. [环境要求](#环境要求)
3. [快速开始](#快速开始)
4. [详细配置](#详细配置)
5. [Docker 部署](#docker-部署)
6. [Windows 服务部署](#windows-服务部署)
7. [Linux 系统部署](#linux-系统部署)
8. [Nginx 反向代理](#nginx-反向代理推荐)
9. [HTTPS 配置](#https-配置)
10. [监控和日志](#监控和日志)
11. [备份和恢复](#备份和恢复)
12. [故障排除](#故障排除)
13. [安全建议](#安全建议)

---

## 概述

本文档介绍如何将视频标签管理系统部署到生产环境，使用 Waitress WSGI 服务器替代 Flask 开发服务器。

### 部署架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│   Waitress  │────▶│   Flask     │
│  (反向代理)  │     │  (WSGI服务器) │     │  (应用)     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                        │
       ▼                                        ▼
┌─────────────┐                         ┌─────────────┐
│  静态文件    │                         │   SQLite    │
│  (CSS/JS)   │                         │  (数据库)    │
└─────────────┘                         └─────────────┘
```

## 环境要求

### 硬件要求

| 配置项 | 最低要求 | 推荐配置 |
|--------|----------|----------|
| CPU | 2核 | 4核+ |
| 内存 | 2GB | 4GB+ |
| 磁盘 | 10GB | 根据视频量决定 |
| 网络 | 100Mbps | 1Gbps |

### 软件要求

- Python 3.8+ (推荐 3.10+)
- Windows/Linux/macOS
- SQLite 3.x
- FFmpeg (可选，用于缩略图生成)

## 快速开始

### 1. 安装依赖

```bash
# 安装基础依赖
pip install -r requirements.txt

# 安装生产服务器
pip install waitress
```

### 2. 配置环境变量

```bash
# 复制配置文件模板
copy .env.example .env

# 编辑 .env 文件，修改以下关键配置：
# - VIDEO_BASE_PATH: 视频文件实际路径
# - SECRET_KEY: 生产环境密钥（必须修改！）
# - HOST/PORT: 服务器监听地址和端口
```

### 3. 启动生产服务器

```bash
# 使用默认配置启动
python run_production.py

# 自定义端口和线程数
python run_production.py -p 8080 -t 8

# 仅检查环境
python run_production.py --check-only
```

## 详细配置

### 服务器配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| HOST | 监听地址 | 0.0.0.0 |
| PORT | 监听端口 | 5000 |
| WORKER_THREADS | 工作线程数 | 4 |

**线程数建议**：
- CPU 4核以下：4线程
- CPU 4-8核：8线程
- CPU 8核以上：16线程

### 安全配置

**必须修改的配置**：

1. **SECRET_KEY**: 生产环境必须修改
   ```bash
   # 生成新密钥
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **SESSION_COOKIE_SECURE**: HTTPS环境下启用
   ```env
   SESSION_COOKIE_SECURE=True  # 仅HTTPS
   ```

3. **视频路径权限**: 确保应用有读取权限

### 性能优化

#### 数据库优化

```bash
# 运行数据库索引优化
python tools/optimize_database_indexes.py

# 测试数据库性能
python tools/test_database_performance.py
```

#### 服务器优化

```python
# run_production.py 中的优化参数
serve(
    app,
    host=host,
    port=port,
    threads=threads,
    channel_timeout=300,        # 连接超时
    cleanup_interval=30,        # 清理间隔
    max_request_body_size=1073741824,  # 1GB
    expose_tracebacks=False     # 不暴露错误堆栈
)
```

## Windows 服务部署

### 使用 NSSM 创建 Windows 服务

1. 下载 NSSM: https://nssm.cc/download

2. 创建服务：
```cmd
nssm install VideoTagSystem
```

3. 配置服务：
- Path: `C:\Python39\python.exe`
- Startup directory: `E:\BaiduSyncdisk\Program20260115\Film_tag_classification_library_V2`
- Arguments: `run_production.py`

4. 启动服务：
```cmd
nssm start VideoTagSystem
```

## Linux 系统部署

### 使用 Systemd

创建服务文件 `/etc/systemd/system/videotag.service`：

```ini
[Unit]
Description=Video Tag System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/videotag
Environment=PATH=/opt/videotag/venv/bin
ExecStart=/opt/videotag/venv/bin/python run_production.py -H 0.0.0.0 -p 5000 -t 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable videotag
sudo systemctl start videotag
```

## Nginx 反向代理（推荐）

### Nginx 配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 视频流优化
        proxy_buffering off;
        proxy_request_buffering off;
        
        # 超时设置
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # 静态文件缓存
    location /static/ {
        alias /opt/videotag/web/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Docker 部署

### Dockerfile

创建 `Dockerfile`：

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install waitress

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p logs backups

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "run_production.py", "-H", "0.0.0.0", "-p", "5000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  videotag:
    build: .
    container_name: videotag
    ports:
      - "5000:5000"
    volumes:
      - ./video_library.db:/app/video_library.db
      - ./backups:/app/backups
      - ./logs:/app/logs
      - ${VIDEO_BASE_PATH}:/videos:ro
    environment:
      - VIDEO_BASE_PATH=/videos
      - SECRET_KEY=${SECRET_KEY}
      - FLASK_ENV=production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/v1/stats"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Docker 部署命令

```bash
# 构建镜像
docker build -t videotag:latest .

# 运行容器
docker run -d \
  --name videotag \
  -p 5000:5000 \
  -v $(pwd)/video_library.db:/app/video_library.db \
  -v /path/to/videos:/videos:ro \
  -e VIDEO_BASE_PATH=/videos \
  -e SECRET_KEY=your-secret-key \
  videotag:latest

# 使用 docker-compose
docker-compose up -d
```

## HTTPS 配置

### 使用 Let's Encrypt (推荐)

1. 安装 Certbot：
```bash
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx

# CentOS
sudo yum install certbot python3-certbot-nginx
```

2. 获取证书：
```bash
sudo certbot --nginx -d your-domain.com
```

3. 自动续期：
```bash
sudo certbot renew --dry-run
```

### 手动配置 HTTPS

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_buffering off;
        proxy_request_buffering off;
    }
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

### Flask HTTPS 配置

在 `.env` 文件中添加：

```env
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
```

## 监控和日志

### 查看日志

```bash
# 实时查看日志
tail -f logs/app.log

# Windows 使用 PowerShell
Get-Content logs/app.log -Wait
```

### 性能监控

```bash
# 测试服务器性能
python tools/test_database_performance.py
```

## 备份和恢复

### 自动备份脚本

创建 `backup.bat` (Windows) 或 `backup.sh` (Linux)：

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
cp video_library.db backups/video_library_$DATE.db
# 保留最近30个备份
ls -t backups/video_library_*.db | tail -n +31 | xargs rm -f
```

### 定时任务

Windows 任务计划程序或 Linux crontab：

```bash
# 每天凌晨3点备份
0 3 * * * /opt/videotag/backup.sh
```

## 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 查看端口占用
   netstat -ano | findstr :5000
   
   # 更换端口启动
   python run_production.py -p 8080
   ```

2. **权限不足**
   ```bash
   # Windows: 以管理员身份运行
   # Linux: 修改文件权限
   chmod -R 755 /opt/videotag
   ```

3. **视频无法播放**
   - 检查 VIDEO_BASE_PATH 配置
   - 确认视频文件存在
   - 检查文件读取权限

4. **数据库锁定**
   - 检查是否有其他进程占用数据库
   - 重启服务

### 性能问题

1. **响应慢**
   - 增加 WORKER_THREADS
   - 运行数据库优化脚本
   - 检查磁盘 I/O

2. **内存占用高**
   - 减少线程数
   - 优化缩略图生成配置

## 更新部署

```bash
# 1. 备份数据
copy video_library.db video_library.db.backup

# 2. 拉取更新
git pull

# 3. 更新依赖
pip install -r requirements.txt

# 4. 重启服务
# Windows 服务
nssm restart VideoTagSystem

# Linux 服务
sudo systemctl restart videotag
```

## 安全建议

### 1. 密码安全

- **修改默认密码**: 首次登录后立即修改默认密码
- **密码复杂度**: 使用至少8位，包含大小写字母、数字和特殊字符
- **定期更换**: 建议每3-6个月更换一次密码

### 2. 网络安全

- **使用 HTTPS**: 生产环境必须启用 HTTPS
- **配置防火墙**: 只开放必要端口（80、443）
- **限制访问**: 可配置 IP 白名单限制访问

```nginx
# Nginx IP 白名单
location / {
    allow 192.168.1.0/24;
    allow 10.0.0.0/8;
    deny all;
    proxy_pass http://127.0.0.1:5000;
}
```

### 3. 应用安全

- **修改 SECRET_KEY**: 生产环境必须修改
- **关闭调试模式**: 确保 `FLASK_DEBUG=false`
- **会话超时**: 设置合理的会话超时时间

### 4. 文件权限

```bash
# Linux 文件权限设置
chmod 600 .env                    # 配置文件仅所有者可读写
chmod 600 video_library.db        # 数据库仅所有者可读写
chmod 755 web/static              # 静态文件可读
chmod -R 755 backups              # 备份目录
```

### 5. 定期更新

```bash
# 更新 Python 依赖
pip install --upgrade pip
pip install --upgrade -r requirements.txt

# 检查安全漏洞
pip install safety
safety check
```

### 6. 日志审计

- 启用访问日志记录
- 定期检查异常登录
- 监控 API 调用频率

### 7. 备份策略

- 每日自动备份数据库
- 异地备份重要数据
- 定期测试恢复流程

---

## 性能调优

### 数据库优化

```bash
# 运行索引优化
python tools/optimize_database_indexes.py

# 定期 VACUUM（SQLite）
sqlite3 video_library.db "VACUUM;"
```

### 缓存配置

```env
# 缓存配置
CACHE_CLEANUP_INTERVAL=300        # 缓存清理间隔（秒）
CACHE_MAX_SIZE=1000               # 最大缓存条目数
```

### 视频流优化

```python
# run_production.py 参数调优
VIDEO_STREAM_CHUNK_SIZE = 1024 * 1024    # 1MB 块大小
VIDEO_CACHE_MAX_AGE = 3600               # 缓存时间
VIDEO_STREAM_BUFFER_SIZE = 64 * 1024     # 缓冲区大小
```

---

## 相关文档

如有问题，请查看：
- [USER_GUIDE.md](USER_GUIDE.md) - 用户使用手册
- [DATABASE_OPTIMIZATION.md](DATABASE_OPTIMIZATION.md) - 数据库优化说明
- [API 文档](/api/docs) - 交互式 API 文档
