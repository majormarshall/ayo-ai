"""
AYO AI — Android Phone Bridge (ADB over Wi-Fi)
================================================
Controls your Android phone from the PC using ADB.
Supports: open apps, send texts, make calls, volume, screenshot,
          swipe/tap gestures, and more.

Setup (one-time):
  1. Enable Developer Options on Android
  2. Turn on USB Debugging
  3. Connect via USB once, run: adb tcpip 5555
  4. Disconnect USB — Ayo will connect over Wi-Fi automatically
"""

import subprocess
import logging
import time
from pathlib import Path

log = logging.getLogger("ayo.phone")

# Android package names for common apps
ANDROID_APPS = {
    "whatsapp":   "com.whatsapp",
    "telegram":   "org.telegram.messenger",
    "instagram":  "com.instagram.android",
    "twitter":    "com.twitter.android",
    "x":          "com.twitter.android",
    "facebook":   "com.facebook.katana",
    "youtube":    "com.google.android.youtube",
    "chrome":     "com.android.chrome",
    "camera":     "com.android.camera2",
    "gallery":    "com.google.android.apps.photos",
    "contacts":   "com.android.contacts",
    "dialer":     "com.android.dialer",
    "settings":   "com.android.settings",
    "spotify":    "com.spotify.music",
    "maps":       "com.google.android.apps.maps",
    "gmail":      "com.google.android.gm",
    "calculator": "com.android.calculator2",
    "clock":      "com.android.deskclock",
}


class PhoneBridge:
    def __init__(self, ip: str = None, port: int = 5555):
        self.ip   = ip
        self.port = port
        self._connected = False
        if ip:
            self.connect(ip, port)

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self, ip: str, port: int = 5555) -> str:
        self.ip   = ip
        self.port = port
        result = self._adb(f"connect {ip}:{port}", no_device=True)
        if "connected" in result.lower():
            self._connected = True
            log.info(f"📱 Phone connected: {ip}:{port}")
            return f"Connected to phone at {ip}."
        log.error(f"Phone connect failed: {result}")
        return f"Couldn't connect to {ip}. Make sure ADB is enabled and the phone is on the same Wi-Fi."

    def disconnect(self) -> str:
        result = self._adb(f"disconnect {self.ip}:{self.port}", no_device=True)
        self._connected = False
        return "Phone disconnected."

    def is_connected(self) -> bool:
        return self._connected

    # ── Apps ──────────────────────────────────────────────────────────────────

    def open_app(self, app: str) -> str:
        package = ANDROID_APPS.get(app.lower().strip(), app)
        result  = self._adb(
            f'shell monkey -p {package} -c android.intent.category.LAUNCHER 1'
        )
        if "error" in result.lower():
            return f"Couldn't open {app} on phone. Is it installed?"
        return f"Opening {app} on phone."

    def close_app(self, app: str) -> str:
        package = ANDROID_APPS.get(app.lower().strip(), app)
        self._adb(f"shell am force-stop {package}")
        return f"Closed {app} on phone."

    # ── Calls & Messages ──────────────────────────────────────────────────────

    def make_call(self, number: str) -> str:
        self._adb(f"shell am start -a android.intent.action.CALL -d tel:{number}")
        return f"Calling {number}."

    def send_sms(self, number: str, message: str) -> str:
        self._adb(
            f'shell am start -a android.intent.action.SENDTO '
            f'-d sms:{number} --es sms_body "{message}" --ez exit_on_sent true'
        )
        return f"Opening SMS to {number}."

    # ── Media & System ────────────────────────────────────────────────────────

    def volume_up(self, steps: int = 3) -> str:
        for _ in range(steps):
            self._adb("shell input keyevent 24")
        return f"Volume up on phone."

    def volume_down(self, steps: int = 3) -> str:
        for _ in range(steps):
            self._adb("shell input keyevent 25")
        return f"Volume down on phone."

    def mute(self) -> str:
        self._adb("shell input keyevent 164")
        return "Phone muted."

    def screenshot(self, save_path: str = None) -> str:
        remote = "/sdcard/ayo_screen.png"
        self._adb(f"shell screencap -p {remote}")
        if not save_path:
            from datetime import datetime
            docs = Path.home() / "Pictures" / "Ayo"
            docs.mkdir(parents=True, exist_ok=True)
            save_path = str(docs / f"phone_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        self._adb(f"pull {remote} \"{save_path}\"")
        return f"Phone screenshot saved to {save_path}."

    def lock_screen(self) -> str:
        self._adb("shell input keyevent 26")
        return "Phone screen locked."

    def unlock_screen(self) -> str:
        self._adb("shell input keyevent 82")
        return "Phone screen unlocked."

    def home(self) -> str:
        self._adb("shell input keyevent 3")
        return "Pressed Home on phone."

    def back(self) -> str:
        self._adb("shell input keyevent 4")
        return "Pressed Back on phone."

    def type_text(self, text: str) -> str:
        safe = text.replace(" ", "%s").replace("'", "\\'")
        self._adb(f"shell input text '{safe}'")
        return f"Typed text on phone."

    def tap(self, x: int, y: int) -> str:
        self._adb(f"shell input tap {x} {y}")
        return f"Tapped ({x}, {y}) on phone screen."

    # ── Battery & Status ──────────────────────────────────────────────────────

    def battery_status(self) -> str:
        result = self._adb("shell dumpsys battery | grep level")
        level  = result.strip().split()[-1] if result else "unknown"
        return f"Phone battery is at {level}%."

    def get_device_info(self) -> dict:
        model   = self._adb("shell getprop ro.product.model").strip()
        android = self._adb("shell getprop ro.build.version.release").strip()
        return {"model": model, "android": android, "ip": self.ip}

    # ── Internal ──────────────────────────────────────────────────────────────

    def _adb(self, command: str, no_device: bool = False) -> str:
        """Run an ADB command and return stdout."""
        if not no_device and not self._connected:
            return "Phone not connected."
        device_flag = f"-s {self.ip}:{self.port}" if self.ip and not no_device else ""
        full_cmd = f"adb {device_flag} {command}"
        try:
            result = subprocess.run(
                full_cmd, shell=True, capture_output=True,
                text=True, timeout=15, encoding="utf-8", errors="replace"
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return "ADB command timed out."
        except Exception as e:
            log.error(f"ADB error: {e}")
            return str(e)
