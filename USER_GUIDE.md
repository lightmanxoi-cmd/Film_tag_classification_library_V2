# 视频标签分类系统 - 用户使用手册

## 目录

1. [系统简介](#系统简介)
2. [快速开始](#快速开始)
3. [启动方式](#启动方式)
4. [功能详解](#功能详解)
5. [Electron 桌面应用](#electron-桌面应用)
6. [命令行工具](#命令行工具)
7. [API 使用](#api-使用)
8. [常见问题](#常见问题)
9. [快捷键](#快捷键)

---

## 系统简介

视频标签分类系统是一个功能强大的视频管理平台，采用奈飞风格的界面设计，支持视频分类、标签管理、多屏播放等功能。

### 主要特性

- **视频管理**: 支持多种视频格式（MP4、MKV、AVI、MOV、WMV、FLV、WebM等）
- **标签分类**: 层级标签结构，支持多维度分类
- **智能筛选**: 支持多标签组合筛选
- **视频流播放**: 支持HTTP Range请求，流畅拖动播放
- **多屏播放**: 支持同时播放多个视频
- **时钟壁纸**: 视频背景+时钟显示，支持拖拽和滚轮调节
- **随机推荐**: 随机展示视频内容
- **移动端适配**: 完美支持手机和平板设备
- **Electron桌面应用**: 纯净窗口界面，支持全局快捷键

### 系统架构

```
Film_tag_classification_library_V2/
├── web/                    # Web应用
│   ├── api/               # REST API
│   ├── auth/              # 认证模块
│   ├── static/            # 静态资源
│   └── templates/         # HTML模板
├── video_tag_system/       # 核心业务模块
│   ├── core/              # 核心配置
│   ├── models/            # 数据模型
│   ├── repositories/      # 数据访问层
│   ├── services/          # 业务逻辑层
│   └── utils/             # 工具函数
├── tools/                  # 命令行工具
├── electron/              # Electron桌面应用
└── ui/                    # Gradio UI界面
```

---

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 18+（仅Electron应用需要）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置文件

1. 复制配置文件模板：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，设置必要参数：
```env
VIDEO_BASE_PATH=F:\Videos
SECRET_KEY=your-secret-key
DEFAULT_PASSWORD=your-password
```

### 首次登录

1. 启动服务器后，访问 http://localhost:5000
2. 使用默认密码登录（在 `.env` 中设置的 `DEFAULT_PASSWORD`）
3. 登录成功后自动跳转到主页

---

## 启动方式

### 方式一：Web服务器

双击 `start_server.bat` 或运行：
```bash
python web_app.py
```

访问 http://localhost:5000

### 方式二：Electron桌面应用

1. 首次运行需要安装依赖：
```bash
cd electron
npm install
```

2. 启动应用：
```bash
双击 electron/run.bat
```

或在 `electron` 目录下运行：
```bash
npm start
```

### 方式三：浏览器应用模式

双击 `start_app_mode.bat`，以无边框浏览器窗口方式启动。

---

## 功能详解

### 1. 视频库主页

主页是系统的核心界面，包含以下区域：

#### 顶部导航栏

| 元素 | 功能 |
|------|------|
| **VIDEO LIBRARY** | 系统Logo |
| **多级筛选** | 打开高级筛选面板 |
| **随机排列** | 随机打乱视频顺序 |
| **时钟壁纸** | 打开时钟壁纸页面 |
| **多路同播** | 打开多屏播放页面 |
| **随机推荐** | 打开随机推荐页面 |
| **搜索框** | 搜索视频标题 |
| **视频统计** | 显示当前视频总数 |
| **会话计时器** | 显示会话剩余时间 |
| **退出按钮** | 退出登录 |

#### 左侧标签栏

- 显示层级标签结构
- 点击标签筛选视频
- 显示每个标签下的视频数量
- 移动端点击底部"分类"按钮打开

#### 视频网格区域

- 以卡片形式展示视频
- 显示缩略图、标题、时长
- 鼠标悬停显示标签信息
- 点击卡片播放视频

### 2. 视频播放

#### 播放操作

1. 点击视频卡片打开播放器
2. 播放器支持：
   - 播放/暂停
   - 音量调节
   - 全屏切换
   - 进度拖动
   - 倍速播放

#### 视频信息

- 标题：显示视频文件名
- 标签：显示视频关联的标签
- 格式提示：MKV/WMV格式可能无法播放

### 3. 标签筛选

#### 单标签筛选

1. 在左侧标签栏点击标签
2. 视频列表自动更新
3. 顶部显示当前筛选条件
4. 点击"清除"取消筛选

#### 多级筛选

1. 点击顶部"多级筛选"按钮
2. 在弹出面板中选择标签
3. **筛选规则**：
   - 同一分类下多选 = "或"关系
   - 不同分类之间 = "和"关系
4. 点击"应用筛选"执行

**示例**：
- 选择"动作"和"喜剧"（同属类型分类）→ 显示动作片或喜剧片
- 选择"动作"（类型）和"美国"（地区）→ 显示美国的动作片

### 4. 时钟壁纸

时钟壁纸页面提供视频背景+时钟显示功能：

#### 功能特点

- 全屏视频背景播放
- 大号时钟显示（时:分:秒）
- 时钟可拖拽移动
- 鼠标滚轮调节时钟大小
- 浏览模式：分段播放视频

#### 时钟操作

| 操作 | 功能 |
|------|------|
| 拖拽时钟 | 移动时钟位置 |
| 鼠标滚轮 | 调节时钟大小 |
| 重置按钮 | 恢复默认位置和大小 |

#### 状态记忆

- Electron模式下自动记忆时钟位置和大小
- 每10秒自动保存状态
- 下次启动自动恢复

### 5. 多路同播

多路同播页面支持同时播放多个视频：

#### 功能特点

- 支持2x2、3x3等多种布局
- 每个视频独立控制
- 独立音量控制
- 可显示/隐藏时钟

#### 操作说明

| 按钮 | 功能 |
|------|------|
| 播放/暂停 | 控制单个视频 |
| 跳过 | 切换到下一个随机视频 |
| 进度条 | 拖动调整播放进度 |
| 音量 | 调节单个视频音量 |
| Clock | 显示/隐藏时钟 |

### 6. 随机推荐

随机推荐页面提供随机视频播放功能：

#### 功能特点

- 随机选择视频播放
- 快速切换下一个
- 显示视频名称和进度
- 支持播放控制

### 7. 移动端操作

#### 底部导航栏

移动端底部固定显示快捷操作栏：

- **分类**: 打开标签侧边栏
- **筛选**: 打开高级筛选
- **时钟**: 打开时钟壁纸
- **随机**: 打开随机推荐
- **搜索**: 打开搜索栏

#### 手势操作

| 手势 | 功能 |
|------|------|
| 下拉 | 刷新视频列表 |
| 上滑 | 加载更多视频 |
| 左右滑动 | 切换标签 |

---

## Electron 桌面应用

### 功能特性

- 无边框窗口设计
- 自定义标题栏（最小化/最大化/关闭按钮）
- 自动启动后端服务
- 窗口状态记忆（位置、大小）
- 时钟位置和大小记忆
- 全局快捷键支持
- 窗口置顶功能

### 全局快捷键

| 快捷键 | 功能 |
|--------|------|
| `Home` | 切换窗口置顶状态（始终显示在最上层） |
| `End` | 关闭应用程序 |

### 窗口控制

- 窗口可自由调整大小（无最小限制）
- 窗口位置和大小自动记忆
- 每10秒自动保存状态
- 最多保存10条状态记录

### 状态存储

状态数据存储位置：
```
Windows: %APPDATA%\video-library\window-state.json
macOS: ~/Library/Application Support/video-library/window-state.json
Linux: ~/.config/video-library/window-state.json
```

### 构建可执行文件

```bash
cd electron
npm run build
```

构建完成后，在 `dist` 文件夹中找到安装包。

---

## 命令行工具

系统提供丰富的命令行工具用于视频和标签管理。

### video_importer.py - 视频导入工具

导入视频文件到数据库：

```bash
# 导入单个视频
python tools/video_importer.py --path "D:/Videos/movie.mp4" --tag "电影" --subtag "动作"

# 批量导入文件夹
python tools/video_importer.py --path "D:/Videos/Movies" --tag "电影" --recursive

# 模拟运行
python tools/video_importer.py --path "D:/Videos" --tag "测试" --dry-run
```

### tag_manager.py - 标签管理工具

管理标签的创建、删除、重命名等：

```bash
# 列出所有标签
python tools/tag_manager.py list

# 创建一级标签
python tools/tag_manager.py create --name "电影" --level 1

# 创建二级标签
python tools/tag_manager.py create --name "动作" --level 2 --parent "电影"

# 删除标签
python tools/tag_manager.py delete --id 5

# 重命名标签
python tools/tag_manager.py rename --id 5 --new-name "动作片"
```

### video_tag_editor.py - 视频标签编辑器

交互式编辑视频标签：

```bash
# 启动交互模式
python tools/video_tag_editor.py

# 搜索视频
python tools/video_tag_editor.py search --title "复仇者"

# 添加标签
python tools/video_tag_editor.py add --id 123 --tags "科幻,动作"
```

### backup_database.py - 数据库备份工具

```bash
# 创建备份
python tools/backup_database.py create --label "升级前备份"

# 列出备份
python tools/backup_database.py list

# 恢复备份
python tools/backup_database.py restore --file "backups/backup_xxx.db"

# 清理旧备份
python tools/backup_database.py clean --keep 5
```

### delete_videos.py - 视频删除工具

```bash
# 按ID删除
python tools/delete_videos.py by-id --id 123

# 按标题删除
python tools/delete_videos.py by-title --title "测试"

# 删除文件不存在的记录
python tools/delete_videos.py missing
```

### update_video_paths.py - 路径更新工具

```bash
# 更新视频路径
python tools/update_video_paths.py --search-path "D:/NewVideos"

# 仅更新路径不存在的视频
python tools/update_video_paths.py --search-path "D:/NewVideos" --filter-missing
```

---

## API 使用

### API 文档

访问 Swagger UI 文档：http://localhost:5000/api/docs

### 常用 API 接口

#### 获取视频列表

```http
GET /api/v1/videos?page=1&page_size=50&search=关键词
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
    "match_all": false,
    "page": 1,
    "page_size": 50
}
```

#### 高级标签筛选

```http
POST /api/v1/videos/by-tags-advanced
Content-Type: application/json

{
    "tags_by_category": {
        "类型": [1, 2],
        "地区": [5, 6]
    },
    "page": 1,
    "page_size": 50
}
```

#### 视频流播放

```http
GET /api/v1/videos/stream/{video_id}
Range: bytes=0-1023
```

### 响应格式

所有 API 返回统一格式：

```json
{
    "success": true,
    "message": "操作成功",
    "data": {...},
    "cached": false
}
```

---

## 常见问题

### Q: 视频无法播放？

**可能原因**：
1. 视频格式不支持（MKV/WMV可能需要转换）
2. 视频文件路径配置错误
3. 浏览器不支持该格式

**解决方法**：
- 使用 Chrome 或 Firefox 浏览器
- 将视频转换为 MP4 格式
- 检查 VIDEO_BASE_PATH 配置

### Q: 登录后很快退出？

**原因**：会话超时（默认30分钟无活动）

**解决方法**：
- 增加超时时间：修改 `.env` 中的 `INACTIVITY_TIMEOUT`
- 保持页面活动

### Q: Electron应用启动失败？

**可能原因**：
1. Node.js未安装或版本过低
2. 依赖未安装
3. 端口5000被占用

**解决方法**：
- 安装Node.js 18+
- 运行 `npm install` 安装依赖
- 检查端口占用情况

### Q: 时钟组件不显示？

**解决方法**：
- 检查浏览器控制台是否有错误
- 清除浏览器缓存
- 确认时钟位置是否在可视区域内

### Q: 移动端显示异常？

**解决方法**：
- 清除浏览器缓存
- 使用 Chrome 或 Safari 浏览器
- 确保系统版本最新

### Q: 全局快捷键不生效？

**可能原因**：
1. 快捷键被其他程序占用
2. 应用未正确注册快捷键

**解决方法**：
- 关闭可能冲突的程序
- 重启Electron应用

---

## 快捷键

### Web页面快捷键

| 快捷键 | 功能 |
|--------|------|
| `Esc` | 关闭播放器/弹窗 |
| `Space` | 播放/暂停 |
| `F` | 全屏切换 |
| `M` | 静音切换 |
| `←` / `→` | 快退/快进 10秒 |
| `↑` / `↓` | 音量增减 |

### Electron全局快捷键

| 快捷键 | 功能 |
|--------|------|
| `Home` | 切换窗口置顶状态 |
| `End` | 关闭应用程序 |

### 时钟组件操作

| 操作 | 功能 |
|------|------|
| 鼠标滚轮 | 调节时钟大小 |
| 拖拽 | 移动时钟位置 |

---

## 技术支持

如遇问题，请查看：

- [API 文档](/api/docs) - 交互式 API 文档
- [部署文档](DEPLOYMENT.md) - 部署和配置说明
- [数据库优化](DATABASE_OPTIMIZATION.md) - 性能优化指南
- [工具使用指南](tools/README.md) - 命令行工具详细说明

---

## 更新日志

### v2.0.0
- 重构系统架构，模块化设计
- 新增Electron桌面应用
- 新增全局快捷键支持
- 新增窗口状态记忆功能
- 新增时钟组件拖拽和大小调节
- 优化移动端适配
- 改进视频流播放性能

### v1.0.0
- 初始版本发布
- 支持视频管理和标签分类
- 支持多屏播放和随机推荐
- 移动端适配
