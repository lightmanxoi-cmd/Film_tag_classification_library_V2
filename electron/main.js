const { app, BrowserWindow, Menu, shell, dialog, ipcMain, screen } = require('electron');
const path = require('path');
const fs = require('fs');

const SERVER_URL = 'http://localhost:5000';
const SERVER_SCRIPT = path.join(__dirname, '..', 'web_app.py');
const STATE_FILE = path.join(app.getPath('userData'), 'window-state.json');
const MAX_STATE_RECORDS = 10;

let mainWindow = null;
let serverProcess = null;
let stateRecords = [];
let autoSaveInterval = null;

function loadWindowStates() {
    try {
        if (fs.existsSync(STATE_FILE)) {
            const data = fs.readFileSync(STATE_FILE, 'utf8');
            const parsed = JSON.parse(data);
            stateRecords = parsed.records || [];
            console.log('[State] Loaded', stateRecords.length, 'state records from', STATE_FILE);
        }
    } catch (err) {
        console.error('[State] Failed to load window states:', err);
        stateRecords = [];
    }
}

function saveWindowStates() {
    try {
        const data = {
            records: stateRecords
        };
        fs.writeFileSync(STATE_FILE, JSON.stringify(data, null, 2));
        console.log('[State] Saved', stateRecords.length, 'state records');
    } catch (err) {
        console.error('[State] Failed to save window states:', err);
    }
}

function getLatestState() {
    if (stateRecords.length === 0) return null;
    return stateRecords[stateRecords.length - 1];
}

function saveState(clockState) {
    if (!mainWindow) return;
    
    try {
        const bounds = mainWindow.getBounds();
        const isMaximized = mainWindow.isMaximized();
        
        const newRecord = {
            timestamp: Date.now(),
            window: {
                x: bounds.x,
                y: bounds.y,
                width: bounds.width,
                height: bounds.height,
                isMaximized: isMaximized
            },
            clock: clockState || null
        };
        
        stateRecords.push(newRecord);
        
        if (stateRecords.length > MAX_STATE_RECORDS) {
            stateRecords.shift();
        }
        
        saveWindowStates();
        console.log('[State] Saved state record, total:', stateRecords.length);
    } catch (err) {
        console.error('[State] Failed to save state:', err);
    }
}

function getValidWindowState() {
    const latestState = getLatestState();
    if (!latestState || !latestState.window) return null;
    
    const { width, height, x, y } = latestState.window;
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;
    
    if (width < 100 || height < 100) return null;
    if (x < -width || x > screenWidth) return null;
    if (y < 0 || y > screenHeight) return null;
    
    return latestState;
}

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

ipcMain.handle('get-latest-state', () => {
    return getLatestState();
});

ipcMain.on('save-state', (event, clockState) => {
    saveState(clockState);
});

ipcMain.handle('get-window-bounds', () => {
    if (!mainWindow) return null;
    const bounds = mainWindow.getBounds();
    const isMaximized = mainWindow.isMaximized();
    return {
        width: bounds.width,
        height: bounds.height,
        isMaximized: isMaximized
    };
});

function startAutoSave() {
    if (autoSaveInterval) {
        clearInterval(autoSaveInterval);
    }
    
    autoSaveInterval = setInterval(() => {
        mainWindow.webContents.send('request-clock-state');
    }, 10000);
    
    console.log('[State] Auto-save started (every 10 seconds)');
}

function stopAutoSave() {
    if (autoSaveInterval) {
        clearInterval(autoSaveInterval);
        autoSaveInterval = null;
        console.log('[State] Auto-save stopped');
    }
}

function createWindow() {
    loadWindowStates();
    
    const defaultWidth = 1400;
    const defaultHeight = 900;
    const savedState = getValidWindowState();
    
    const windowOptions = {
        width: savedState ? savedState.window.width : defaultWidth,
        height: savedState ? savedState.window.height : defaultHeight,
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
    };
    
    if (savedState && !savedState.window.isMaximized) {
        windowOptions.x = savedState.window.x;
        windowOptions.y = savedState.window.y;
    }

    mainWindow = new BrowserWindow(windowOptions);

    mainWindow.loadURL(SERVER_URL);

    mainWindow.once('ready-to-show', () => {
        if (savedState && savedState.window.isMaximized) {
            mainWindow.maximize();
        }
        mainWindow.show();
        startAutoSave();
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
        stopAutoSave();
        mainWindow = null;
    });

    mainWindow.on('resize', () => {
        mainWindow.webContents.send('window-resized');
    });

    mainWindow.on('move', () => {
        mainWindow.webContents.send('window-moved');
    });

    mainWindow.on('maximize', () => {
        mainWindow.webContents.send('window-maximized');
    });

    mainWindow.on('unmaximize', () => {
        mainWindow.webContents.send('window-unmaximized');
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
    stopAutoSave();
    stopServer();
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    stopAutoSave();
    stopServer();
});

process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception:', error);
});
