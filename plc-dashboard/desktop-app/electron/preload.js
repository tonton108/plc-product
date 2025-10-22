import { contextBridge, ipcRenderer } from 'electron'

// レンダラープロセスに安全にAPIを公開
contextBridge.exposeInMainWorld('electronAPI', {
  /**
   * Flask backendの状態をチェック
   */
  checkFlaskStatus: () => ipcRenderer.invoke('check-flask-status')
})
