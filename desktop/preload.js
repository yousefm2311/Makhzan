const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('desktop', {
  version: process.versions.electron,
});
