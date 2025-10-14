const { contextBridge, ipcRenderer } = require('electron');

// セキュアなIPC通信用APIをレンダラープロセスに公開
contextBridge.exposeInMainWorld('electronAPI', {
  // Docker管理
  dockerStart: () => ipcRenderer.invoke('docker:start'),
  dockerStop: () => ipcRenderer.invoke('docker:stop'),
  dockerRestart: () => ipcRenderer.invoke('docker:restart'),
  dockerStatus: () => ipcRenderer.invoke('docker:status'),

  // ログ管理
  getLogs: (service) => ipcRenderer.invoke('logs:get', service),
  onLogUpdate: (callback) => {
    ipcRenderer.on('logs:update', (event, data) => callback(data));
  },

  // システム情報
  getSystemInfo: () => ipcRenderer.invoke('system:info'),

  // アプリケーション制御
  minimizeToTray: () => ipcRenderer.send('window:minimize-to-tray'),
  showWindow: () => ipcRenderer.send('window:show'),
  quitApp: () => ipcRenderer.send('app:quit'),

  // 設定管理
  getConfig: () => ipcRenderer.invoke('config:get'),
  saveConfig: (config) => ipcRenderer.invoke('config:save', config),

  // 通知
  showNotification: (title, body) => ipcRenderer.send('notification:show', { title, body })
});
