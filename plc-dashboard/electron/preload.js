const { contextBridge, ipcRenderer } = require('electron');

// セキュアなIPC通信用APIをレンダラー（viewer:5001のSPA）に公開する。
// Phase 4でDocker管理からネイティブサービス管理へ刷新（service:*）。
contextBridge.exposeInMainWorld('electronAPI', {
  // サービス管理（plc-ingest / plc-viewer / Memurai）
  serviceStatus: () => ipcRenderer.invoke('service:status'),
  serviceStart: () => ipcRenderer.invoke('service:start'),
  serviceStop: () => ipcRenderer.invoke('service:stop'),
  serviceRestart: () => ipcRenderer.invoke('service:restart'),
  serviceRefresh: () => ipcRenderer.invoke('service:refresh'),
  onServiceStatusUpdate: (callback) => {
    ipcRenderer.on('service:status-update', (_e, data) => callback(data));
  },

  // ログ取得（C:\ProgramData\plc-monitor\logs）
  getLogs: (serviceKey) => ipcRenderer.invoke('logs:get', serviceKey),

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
  showNotification: (title, body) => ipcRenderer.send('notification:show', { title, body }),
});
