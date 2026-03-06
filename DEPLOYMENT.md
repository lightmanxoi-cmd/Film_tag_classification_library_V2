# 生产环境部署指南

## 概述

本文档介绍如何将视频标签管理系统部署到生产环境，使用 Waitress WSGI 服务器替代 Flask 开发服务器。

## 环境要求

- Python 3.8+
- Windows/Linux/macOS
- 至少 2GB 内存
- 足够的磁盘空间存储视频文件

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

1. **修改默认密码**
2. **使用 HTTPS**
3. **配置防火墙**
4. **定期更新依赖**
5. **启用访问日志**
6. **设置文件权限**

## 联系支持

如有问题，请查看：
- [DATABASE_OPTIMIZATION.md](DATABASE_OPTIMIZATION.md) - 数据库优化说明
- [README.md](README.md) - 项目说明
