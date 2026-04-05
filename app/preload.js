const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  saveData: (category, data) => ipcRenderer.invoke('save-data', { category, data }),
  loadData: (category) => ipcRenderer.invoke('load-data', { category }),
  getDashboard: () => ipcRenderer.invoke('get-dashboard'),
  deleteData: (category, filename) => ipcRenderer.invoke('delete-data', { category, filename }),
  updateData: (category, filename, data) => ipcRenderer.invoke('update-data', { category, filename, data }),
  fetchTitleFromUrl: (url) => ipcRenderer.invoke('fetch-title-from-url', { url }),
  cwLogin: () => ipcRenderer.invoke('cw-login'),
  cwLoginStatus: () => ipcRenderer.invoke('cw-login-status')
});
