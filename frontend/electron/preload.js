/**
 * AYO AI — Electron Preload Script
 * Bridges the renderer (frontend) to main process safely.
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("ayoElectron", {
  getApiUrl:  () => ipcRenderer.invoke("get-api-url"),
  minimize:   () => ipcRenderer.send("window-minimize"),
  maximize:   () => ipcRenderer.send("window-maximize"),
  hide:       () => ipcRenderer.send("window-hide"),
  platform:   process.platform,
});
