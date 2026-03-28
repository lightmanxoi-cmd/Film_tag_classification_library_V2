const { app, BrowserWindow, Menu, shell, dialog, ipcMain } = require('electron');
const path = require('path');

const SERVER_URL = 'http://localhost:5000';
const SERVER_SCRIPT = path.join(__dirname, '..', 'web_app.py');

let mainWindow = null;
let serverProcess = null;

ipcMain.on('window-minimize', () => {
    if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
    if (mainWindow) {
        if (mainWindow.isMaximized()) {
            mainWindow.unmaximize();
        } else {
            mainWindow.maximize();
        }
    }
});

ipcMain.on('window-close', () => {
    if (mainWindow) mainWindow.close();
});

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 800,
        minHeight: 600,
        frame: false,
        titleBarStyle: 'hidden',
        backgroundColor: '#141414',
        icon: path.join(__dirname, 'icon.ico'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
            webSecurity: true
        },
        show: false
    });

    mainWindow.loadURL(SERVER_URL);

    mainWindow.once('ready-to-show', () => {
        mainWindow.maximize();
        mainWindow.show();
    });

    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
        console.error('Failed to load:', errorDescription);
        mainWindow.loadURL(`data:text/html,
            <html>
            <head><meta charset="UTF-8"><title>Error</title></head>
            <body style="background:#141414;color:#fff;font-family:sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;">
                <h1 style="color:#e50914;">Connection Failed</h1>
                <p>Cannot connect to server at ${SERVER_URL}</p>
                <p style="color:#888;">Please make sure the server is running.</p>
                <button onclick="location.reload()" style="margin-top:20px;padding:10px 30px;background:#e50914;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:16px;">Retry</button>
            </body>
            </html>
        `);
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    setupMenu();
}

function setupMenu() {
    const template = [
        {
            label: 'View',
            submenu: [
                { role: 'reload' },
                { role: 'forceReload' },
                { type: 'separator' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'togglefullscreen' }
            ]
        },
        {
            label: 'Window',
            submenu: [
                { role: 'minimize' },
                { role: 'close' }
            ]
        },
        {
            label: 'Help',
            submenu: [
                {
                    label: 'About',
                    click: () => {
                        dialog.showMessageBox(mainWindow, {
                            type: 'info',
                            title: 'About Video Library',
                            message: 'Video Library Desktop Application',
                            detail: 'Version: 1.0.0\nA Netflix-style video management system.'
                        });
                    }
                }
            ]
        }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
}

function startServer() {
    const { spawn } = require('child_process');
    
    serverProcess = spawn('python', [SERVER_SCRIPT], {
        cwd: path.dirname(SERVER_SCRIPT),
        stdio: 'inherit'
    });

    serverProcess.on('error', (err) => {
        console.error('Failed to start server:', err);
    });

    serverProcess.on('exit', (code) => {
        console.log(`Server exited with code ${code}`);
        serverProcess = null;
    });
}

function stopServer() {
    if (serverProcess) {
        if (process.platform === 'win32') {
            spawn('taskkill', ['/pid', serverProcess.pid, '/f', '/t']);
        } else {
            serverProcess.kill('SIGTERM');
        }
        serverProcess = null;
    }
}

app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    stopServer();
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    stopServer();
});

process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception:', error);
});
