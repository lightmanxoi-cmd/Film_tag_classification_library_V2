# 🎬 视频标签分类管理系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![SQLite](https://img.shields.io/badge/SQLite-3.x-blue.svg)](https://www.sqlite.org/)

一个功能完善的本地视频库管理解决方案，采用奈飞风格的现代化界面设计，帮助您高效整理、分类和检索个人视频收藏。

![界面预览](docs/screenshot.png)

## ✨ 核心特性

### 🎥 视频管理
- **多格式支持** - MP4、MKV、AVI、MOV、WMV、FLV、WebM 等主流格式
- **批量导入** - 支持文件夹批量扫描，自动提取视频元数据
- **视频流播放** - HTTP Range 请求支持，流畅拖动进度条
- **缩略图生成** - 自动生成视频预览缩略图和 GIF 动图
- **元数据提取** - 自动获取视频时长、分辨率、文件大小等信息

### 🏷️ 标签分类
- **层级标签** - 支持多级标签结构，灵活组织分类体系
- **多标签关联** - 单个视频可关联多个标签
- **标签树可视化** - 直观展示标签层级关系
- **智能筛选** - 支持多标签组合筛选（AND/OR 逻辑）

### 🔍 智能检索
- **关键词搜索** - 按视频标题快速查找
- **标签组合筛选** - 支持复杂的多条件筛选
- **随机推荐** - 随机发现视频内容
- **分页浏览** - 高效处理大量视频

### 🌐 现代化界面
- **奈飞风格设计** - 沉浸式视频浏览体验
- **响应式布局** - 完美适配桌面和移动设备
- **暗色主题** - 护眼舒适的视觉体验
- **多屏播放** - 同时播放多个视频对比观看

### 🔌 开发者友好
- **RESTful API** - 完整的 API 接口，OpenAPI 文档
- **模块化架构** - 清晰的分层设计，易于扩展
- **命令行工具** - 丰富的 CLI 工具集
- **Electron 桌面应用** - 一键启动，无需配置环境

## 📦 快速开始

### 环境要求

| 依赖 | 版本要求 |
|------|----------|
| Python | 3.8+ |
| SQLite | 3.x |
| FFmpeg | 可选（缩略图生成） |
| Node.js | 18+（仅 Electron 应用需要） |

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/lightmanxoi-cmd/Film_tag_classification_library_V2.git
cd Film_tag_classification_library_V2

# 2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
.\venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 VIDEO_BASE_PATH 和密码
```

### 启动服务

```bash
# 方式一：直接启动
python web_app.py

# 方式二：生产模式（Windows）
start_server.bat

# 方式三：Electron 桌面应用
cd electron
npm install
npm start
```

访问 http://localhost:5000 开始使用！

## 📁 项目结构

```
Film_tag_classification_library_V2/
├── 📂 web/                          # Web 应用模块
│   ├── 📂 api/                      # REST API
│   │   ├── 📂 v1/                   # API v1 版本
│   │   │   ├── videos.py            # 视频 API
│   │   │   ├── tags.py              # 标签 API
│   │   │   ├── stats.py             # 统计 API
│   │   │   └── ...
│   │   └── openapi.yaml             # OpenAPI 文档
│   ├── 📂 auth/                     # 认证模块
│   ├── 📂 core/                     # 核心组件
│   │   ├── errors.py                # 错误处理
│   │   ├── cache_decorator.py       # 缓存装饰器
│   │   └── responses.py             # 响应格式
│   ├── 📂 static/                   # 静态资源
│   │   ├── 📂 css/                  # 样式文件
│   │   ├── 📂 js/                   # JavaScript 模块
│   │   └── 📂 images/               # 图片资源
│   ├── 📂 templates/                # HTML 模板
│   └── app.py                       # Flask 应用工厂
│
├── 📂 video_tag_system/             # 核心业务模块
│   ├── 📂 core/                     # 核心配置
│   │   ├── database.py              # 数据库管理
│   │   └── config.py                # 配置管理
│   ├── 📂 models/                   # 数据模型
│   │   ├── video.py                 # 视频模型
│   │   ├── tag.py                   # 标签模型
│   │   └── video_tag.py             # 关联模型
│   ├── 📂 repositories/             # 数据访问层
│   ├── 📂 services/                 # 业务逻辑层
│   └── 📂 utils/                    # 工具函数
│
├── 📂 tools/                        # 命令行工具
│   ├── video_importer.py            # 视频导入工具
│   ├── tag_manager.py               # 标签管理工具
│   ├── video_tag_editor.py          # 标签编辑工具
│   ├── backup_database.py           # 数据库备份工具
│   └── ...
│
├── 📂 electron/                     # Electron 桌面应用
│   ├── main.js                      # 主进程
│   ├── preload.js                   # 预加载脚本
│   └── package.json                 # 依赖配置
│
├── 📂 tests/                        # 测试文件
├── 📄 requirements.txt              # Python 依赖
├── 📄 pyproject.toml                # 项目配置
└── 📄 web_app.py                    # 应用入口
```

## 🛠️ 功能详解

### 视频管理

#### 导入视频

```bash
# 导入单个视频
python tools/video_importer.py --path "D:/Videos/movie.mp4" --tag "电影"

# 批量导入文件夹
python tools/video_importer.py --path "D:/Videos/Movies" --tag "电影" --recursive
```

#### 视频播放

- 支持拖动进度条
- 支持倍速播放
- 支持全屏模式
- 支持多屏同时播放

### 标签管理

```bash
# 列出所有标签
python tools/tag_manager.py list

# 创建标签
python tools/tag_manager.py create --name "科幻" --level 1
python tools/tag_manager.py create --name "动作" --level 2 --parent "科幻"

# 合并标签
python tools/tag_manager.py merge --source 3 --target 5
```

### Web 界面操作

| 功能 | 操作 |
|------|------|
| 筛选视频 | 点击左侧标签树 |
| 多标签筛选 | 按住 Ctrl 点击多个标签 |
| 搜索视频 | 顶部搜索框输入关键词 |
| 编辑标签 | 视频卡片上的标签按钮 |
| 播放视频 | 点击视频缩略图 |

## 🔌 API 文档

### 基础 URL

```
http://localhost:5000/api/v1
```

### 认证

所有 API 需要通过 Session 认证，先调用登录接口：

```bash
curl -X POST http://localhost:5000/login \
  -d "password=your_password" \
  -c cookies.txt
```

### 主要接口

#### 获取视频列表

```http
GET /api/v1/videos?page=1&page_size=20
```

#### 获取标签树

```http
GET /api/v1/tags/tree
```

#### 按标签筛选视频

```http
POST /api/v1/videos/by-tags
Content-Type: application/json

{
  "tag_ids": [1, 2, 3],
  "logic": "AND"
}
```

#### 获取统计数据

```http
GET /api/v1/stats
```

完整 API 文档请访问：http://localhost:5000/api/docs

## 🖥️ Electron 桌面应用

### 安装

```bash
cd electron
npm install
```

### 启动

```bash
# 开发模式
npm start

# 构建应用
npm run build
```

### 特性

- 纯净窗口界面，无浏览器边框
- 全局快捷键支持
- 系统托盘图标
- 自动更新检测

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Frontend)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  HTML/CSS   │  │ JavaScript  │  │  Electron   │         │
│  │  Templates  │  │   Modules   │  │   Desktop   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        API 层 (REST API)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Videos    │  │    Tags     │  │    Stats    │         │
│  │    API      │  │    API      │  │    API      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      业务逻辑层 (Services)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ VideoService│  │ TagService  │  │VideoTagSvc  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据访问层 (Repositories)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │VideoRepo    │  │  TagRepo    │  │VideoTagRepo │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       数据层 (Database)                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    SQLite Database                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 配置说明

### 环境变量 (.env)

```env
# 视频文件基础路径
VIDEO_BASE_PATH=F:\Videos

# Flask 密钥（生产环境必须修改）
SECRET_KEY=your-secret-key-here

# 默认登录密码
DEFAULT_PASSWORD=your-password

# 服务器配置
HOST=0.0.0.0
PORT=5000

# 数据库路径
DATABASE_URL=sqlite:///./video_tag_system.db

# 缩略图配置
THUMBNAIL_WIDTH=320
THUMBNAIL_HEIGHT=180
```

### 数据库配置

系统默认使用 SQLite 数据库，首次启动会自动创建表结构。

```python
from video_tag_system import DatabaseManager

db = DatabaseManager(database_url="sqlite:///./my_videos.db")
db.create_tables()
```

## 🚀 生产部署

### 使用 Waitress (推荐)

```bash
pip install waitress
python run_production.py
```

### Docker 部署

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "run_production.py"]
```

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /path/to/app/web/static/;
    }
}
```

详细部署指南请参考 [DEPLOYMENT.md](DEPLOYMENT.md)

## 🧪 测试

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest

# 测试覆盖率
pytest --cov=video_tag_system --cov-report=html
```

## 📝 开发指南

### 代码风格

```bash
# 格式化代码
black .

# 检查代码风格
flake8

# 类型检查
mypy video_tag_system
```

### 添加新的 API 端点

1. 在 `web/api/v1/` 创建新的蓝图文件
2. 在 `web/api/v1/__init__.py` 注册蓝图
3. 在 `web/api/openapi.yaml` 添加文档

### 添加新的服务

1. 在 `video_tag_system/models/` 定义数据模型
2. 在 `video_tag_system/repositories/` 创建数据访问层
3. 在 `video_tag_system/services/` 实现业务逻辑

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [Electron](https://www.electronjs.org/) - 桌面应用框架
- [FFmpeg](https://ffmpeg.org/) - 视频处理

## 📮 联系方式

如有问题或建议，欢迎提交 [Issue](https://github.com/lightmanxoi-cmd/Film_tag_classification_library_V2/issues)

---

⭐ 如果这个项目对您有帮助，请给一个 Star！
