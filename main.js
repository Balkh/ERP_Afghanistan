const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const db = require('./db/models');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  // Load the Vite dev server in development, or the built files in production
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173');
    // Open DevTools
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
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
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Handle IPC messages from renderer
ipcMain.handle('db:query', async (event, query, params) => {
  try {
    // For now, we'll handle specific queries
    // In a real implementation, you might want a more flexible query system
    if (query === 'getProducts') {
      const products = await db.Product.findAll();
      return products;
    } else if (query === 'getSuppliers') {
      const suppliers = await db.Supplier.findAll();
      return suppliers;
    } else if (query === 'getCustomers') {
      const customers = await db.Customer.findAll();
      return customers;
    } else {
      // Default fallback
      return [];
    }
  } catch (error) {
    console.error('Database query error:', error);
    throw error;
  }
});

// Expose db models to ipcMain for direct use if needed
ipcMain.handle('db:getModels', () => {
  return db;
});