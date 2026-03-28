# Video Library - Electron Desktop App

Electron桌面应用版本，提供纯净的窗口界面。

## 前置要求

1. **Node.js** (v18 或更高版本)
   - 下载: https://nodejs.org/

2. **Python环境** (用于后端服务)
   - 确保可以运行 `web_app.py`

## 快速启动

### 方式一：双击启动脚本
```
双击 start.bat
```

### 方式二：命令行启动
```bash
cd electron
npm install    # 首次运行需要安装依赖
npm start      # 启动应用
```

## 构建可执行文件

### 构建安装包
```bash
双击 build.bat
```

或命令行：
```bash
cd electron
npm run build
```

构建完成后，在 `dist` 文件夹中找到安装包。

## 功能特性

- 无边框窗口设计
- 自定义标题栏（最小化/最大化/关闭按钮）
- 自动启动后端服务
- 纯净的浏览体验

## 目录结构

```
electron/
├── package.json      # 项目配置
├── main.js           # Electron主进程
├── preload.js        # 预加载脚本
├── start.bat         # 启动脚本
├── build.bat         # 构建脚本
└── README.md         # 说明文档
```

## 注意事项

1. 首次运行会自动安装依赖，需要等待几分钟
2. 确保端口 5000 未被其他程序占用
3. 如需自定义图标，替换 `icon.ico` 文件

## 常见问题

### Q: 启动后显示连接失败？
A: 检查后端服务是否正常运行，确保 Python 环境正确配置。

### Q: 如何修改默认端口？
A: 编辑 `main.js` 中的 `SERVER_URL` 变量。

### Q: 构建失败？
A: 确保已安装所有依赖，尝试删除 `node_modules` 文件夹后重新运行 `npm install`。
