const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    minimize: () => ipcRenderer.send('window-minimize'),
    maximize: () => ipcRenderer.send('window-maximize'),
    close: () => ipcRenderer.send('window-close'),
    isElectron: true,
    
    getLatestState: () => ipcRenderer.invoke('get-latest-state'),
    saveState: (clockState) => ipcRenderer.send('save-state', clockState),
    getWindowBounds: () => ipcRenderer.invoke('get-window-bounds'),
    
    onRequestClockState: (callback) => {
        ipcRenderer.on('request-clock-state', () => callback());
    },
    
    onWindowResized: (callback) => {
        ipcRenderer.on('window-resized', () => callback());
    },
    
    onWindowMoved: (callback) => {
        ipcRenderer.on('window-moved', () => callback());
    },
    
    onWindowMaximized: (callback) => {
        ipcRenderer.on('window-maximized', () => callback());
    },
    
    onWindowUnmaximized: (callback) => {
        ipcRenderer.on('window-unmaximized', () => callback());
    }
});
