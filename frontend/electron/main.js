/**
 * AYO AI — Electron Main Process
 * ================================
 * Launches the Python backend as a child process,
 * waits for it to be ready, then opens the dashboard window.
 */

const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, nativeImage } = require("electron");
const path   = require("path");
const { spawn } = require("child_process");
const http   = require("http");

const isDev = process.argv.includes("--dev");
const API_PORT = 5050;
const API_URL  = `http://localhost:${API_PORT}`;

let mainWindow = null;
let tray       = null;
let pyProcess  = null;

// ── Python Backend ────────────────────────────────────────────────────────────

function startPythonBackend() {
  const rootDir  = path.join(__dirname, "..", "..");
  const mainPy   = path.join(rootDir, "main.py");
  const pythonExe = process.platform === "win32" ? "python" : "python3";

  console.log("🐍 Starting Python backend…");
  pyProcess = spawn(pythonExe, [mainPy], {
    cwd:   rootDir,
    stdio: ["pipe", "pipe", "pipe"],
  });

  pyProcess.stdout.on("data", (d) => console.log("[Python]", d.toString().trim()));
  pyProcess.stderr.on("data", (d) => console.error("[Python ERR]", d.toString().trim()));
  pyProcess.on("close", (code) => console.log(`Python exited: ${code}`));
}

function waitForBackend(maxRetries = 30, interval = 1000) {
  return new Promise((resolve, reject) => {
    let tries = 0;
    const check = () => {
      http.get(`${API_URL}/api/status`, (res) => {
        if (res.statusCode === 200) resolve();
        else retry();
      }).on("error", retry);
    };
    const retry = () => {
      tries++;
      if (tries >= maxRetries) reject(new Error("Backend did not start in time."));
      else setTimeout(check, interval);
    };
    check();
  });
}

// ── Window ────────────────────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width:           1400,
    height:          900,
    minWidth:        900,
    minHeight:       600,
    frame:           false,      // Custom title bar
    transparent:     false,
    backgroundColor: "#0F172A",
    icon:            path.join(__dirname, "..", "src", "assets", "ayo-icon.png"),
    webPreferences: {
      nodeIntegration:     false,
      contextIsolation:    true,
      preload:             path.join(__dirname, "preload.js"),
    },
  });

  mainWindow.loadFile(path.join(__dirname, "..", "src", "index.html"));

  if (isDev) mainWindow.webContents.openDevTools();

  mainWindow.on("close", (e) => {
    e.preventDefault();
    mainWindow.hide();   // Minimize to tray instead of closing
  });
}

// ── System Tray ───────────────────────────────────────────────────────────────

function createTray() {
  try {
    const iconPath = path.join(__dirname, "..", "src", "assets", "ayo-tray.png");
    tray = new Tray(iconPath);
    tray.setToolTip("Ayo AI — Always Listening");

    const menu = Menu.buildFromTemplate([
      { label: "Open Ayo Dashboard", click: () => { mainWindow.show(); mainWindow.focus(); } },
      { label: "Pause Listening",    click: () => { /* TODO: pause wake detector */ } },
      { type:  "separator" },
      { label: "Exit Ayo AI",        click: () => { app.quit(); } },
    ]);

    tray.setContextMenu(menu);
    tray.on("double-click", () => { mainWindow.show(); mainWindow.focus(); });
  } catch (e) {
    console.warn("Tray icon not found, skipping system tray:", e.message);
  }
}

// ── IPC Handlers (renderer ↔ main) ───────────────────────────────────────────

ipcMain.handle("get-api-url", () => API_URL);

ipcMain.on("window-minimize", () => mainWindow.minimize());
ipcMain.on("window-maximize", () => {
  mainWindow.isMaximized() ? mainWindow.restore() : mainWindow.maximize();
});
ipcMain.on("window-hide",  () => mainWindow.hide());

// ── App Lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  startPythonBackend();

  console.log("⏳ Waiting for Python backend…");
  try {
    await waitForBackend();
    console.log("✅ Backend ready!");
  } catch (e) {
    console.error("Backend timeout — opening dashboard anyway.");
  }

  createWindow();
  createTray();

  // Global hotkey: Ctrl+Shift+A → show/hide dashboard
  globalShortcut.register("Control+Shift+A", () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
    }
  });
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
  if (pyProcess) pyProcess.kill();
});

app.on("window-all-closed", () => {
  // Don't quit on window close — stay in tray
});

app.on("activate", () => {
  if (mainWindow) mainWindow.show();
});
