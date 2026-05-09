// Preload scripts for Electron
const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to the renderer
contextBridge.exposeInMainWorld('electronAPI', {
  // Database queries
  dbQuery: (query, params) => ipcRenderer.invoke('db:query', query, params),
  // Add more IPC methods as needed
});

// Expose database service to renderer
contextBridge.exposeInMainWorld('databaseService', {
  // Products
  getProducts: () => ipcRenderer.invoke('db:query', 'getProducts'),
  getSuppliers: () => ipcRenderer.invoke('db:query', 'getSuppliers'),
  getCustomers: () => ipcRenderer.invoke('db:query', 'getCustomers'),
  // Add more methods as needed
});