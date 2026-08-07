"""
AYO AI — System Control Tools
==============================
Controls the Windows PC on Ayo's behalf:
- Open/close applications
- Volume and brightness
- File operations
- Screenshots
- Window management
"""

import subprocess
import logging
import os
import shutil
import glob
from pathlib import Path
import pyautogui
import psutil

log = logging.getLogger("ayo.system")

# Common app name → executable mappings
APP_MAP = {
    "notepad":       "notepad.exe",
    "calculator":    "calc.exe",
    "chrome":        "chrome",
    "google chrome": "chrome",
    "firefox":       "firefox",
    "edge":          "msedge",
    "word":          "winword",
    "excel":         "excel",
    "powerpoint":    "powerpnt",
    "vlc":           "vlc",
    "file explorer": "explorer",
    "explorer":      "explorer",
    "task manager":  "taskmgr",
    "settings":      "ms-settings:",
    "paint":         "mspaint",
    "vs code":       "code",
    "vscode":        "code",
    "spotify":       "spotify",
    "whatsapp":      "whatsapp",
    "telegram":      "telegram",
}


def open_app(app: str) -> str:
    """Open an application by name."""
    name = app.lower().strip()
    exe  = APP_MAP.get(name, app)
    try:
        if exe.startswith("ms-"):
            subprocess.Popen(["start", exe], shell=True)
        else:
            subprocess.Popen(exe, shell=True)
        return f"Opening {app}."
    except Exception as e:
        log.error(f"open_app error: {e}")
        return f"I couldn't open {app}. Make sure it's installed."


def close_app(app: str) -> str:
    """Close a running application by name."""
    name = app.lower().strip()
    for proc in psutil.process_iter(["name", "pid"]):
        if name in proc.info["name"].lower():
            proc.kill()
            return f"Closed {app}."
    return f"I couldn't find {app} running."


def take_screenshot(save_path: str = None) -> str:
    """Take a screenshot and save it."""
    docs = Path.home() / "Pictures" / "Ayo"
    docs.mkdir(parents=True, exist_ok=True)
    if not save_path:
        from datetime import datetime
        fname = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        save_path = str(docs / fname)
    img = pyautogui.screenshot()
    img.save(save_path)
    log.info(f"📸 Screenshot saved: {save_path}")
    return f"Screenshot saved to {save_path}"


def set_volume(level: int) -> str:
    """Set system volume (0–100)."""
    level = max(0, min(100, int(level)))
    try:
        # Windows: use nircmd or PowerShell
        ps_cmd = (
            f"[audio]::Volume = {level / 100}; "
            f"Add-Type -TypeDefinition 'using System.Runtime.InteropServices; "
            f"[Guid(\"5CDF2C82-841E-4546-9722-0CF74078229A\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] "
            f"interface IAudioEndpointVolume {{ void _vf1(); void _vf2(); void _vf3(); "
            f"[PreserveSig] int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext); }}'"
        )
        # Simpler approach via nircmd (if installed) or PowerShell
        subprocess.run(
            ["powershell", "-c",
             f"(New-Object -ComObject WScript.Shell).SendKeys([char]173)" if level == 0 else
             f"$vol = New-Object -ComObject WScript.Shell; "
             f"for($i=0;$i -lt 50;$i++){{$vol.SendKeys([char]174)}}; "
             f"for($i=0;$i -lt {level//2};$i++){{$vol.SendKeys([char]175)}}"],
            shell=True, capture_output=True
        )
        return f"Volume set to {level}%."
    except Exception as e:
        log.error(f"set_volume error: {e}")
        return "I couldn't change the volume right now."


def list_files(directory: str = None) -> str:
    """List files in a directory."""
    path = Path(directory) if directory else Path.home()
    try:
        items = list(path.iterdir())
        files = [f.name for f in items if f.is_file()][:20]
        dirs  = [f.name + "/" for f in items if f.is_dir()][:10]
        result = dirs + files
        return "Files found:\n" + "\n".join(result) if result else "Directory is empty."
    except Exception as e:
        return f"Couldn't read {path}: {e}"


def read_file(path: str) -> str:
    """Read and return contents of a text file."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"Couldn't read file: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"File written to {path}."
    except Exception as e:
        return f"Couldn't write file: {e}"


def search_files(query: str, directory: str = None) -> str:
    """Search for files by name pattern."""
    search_dir = directory or str(Path.home())
    pattern = f"**/*{query}*"
    try:
        results = list(Path(search_dir).glob(pattern))[:10]
        if results:
            return "Found:\n" + "\n".join(str(r) for r in results)
        return f"No files matching '{query}' found."
    except Exception as e:
        return f"Search error: {e}"
