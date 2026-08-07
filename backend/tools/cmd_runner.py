"""
AYO AI — CMD / PowerShell Runner
==================================
Lets Ayo execute terminal commands on the PC with safety checks.
Dangerous commands require explicit confirmation before running.
Output is streamed back and returned as a string.
"""

import subprocess
import logging
import shlex
from pathlib import Path

log = logging.getLogger("ayo.cmd")

# Commands that are BLOCKED outright
BLOCKED_COMMANDS = [
    "rm -rf", "del /f /s /q", "format c:",
    "shutdown /r", "shutdown /s", "rmdir /s",
    "rd /s", "deltree",
]

# Commands that need a confirmation step
WARN_COMMANDS = [
    "del", "rm", "rmdir", "rd", "shutdown",
    "format", "reg delete", "net stop", "taskkill",
]


class CMDRunner:
    def __init__(self, working_dir: str = None):
        self.cwd = working_dir or str(Path.home())

    def run(self, command: str, confirm_dangerous: bool = False) -> dict:
        """
        Execute a command.
        Returns:
          { "output": str, "error": str, "blocked": bool, "needs_confirm": bool }
        """
        cmd_lower = command.lower().strip()

        # Block destructive commands
        for blocked in BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                log.warning(f"⛔ Blocked dangerous command: {command}")
                return {
                    "output": "",
                    "error": f"I blocked that command for safety. '{command}' is too risky.",
                    "blocked": True,
                    "needs_confirm": False,
                }

        # Warn on potentially dangerous commands
        if not confirm_dangerous:
            for warn in WARN_COMMANDS:
                if cmd_lower.startswith(warn) or f" {warn} " in cmd_lower:
                    return {
                        "output": "",
                        "error": "",
                        "blocked": False,
                        "needs_confirm": True,
                        "command": command,
                        "warning": f"'{command}' could modify or delete data. Confirm to proceed.",
                    }

        # Execute
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.cwd,
                encoding="utf-8",
                errors="replace",
            )
            output = result.stdout.strip()
            error  = result.stderr.strip()
            log.info(f"💻 Ran: {command} → exit {result.returncode}")
            return {
                "output": output or "(no output)",
                "error":  error,
                "blocked": False,
                "needs_confirm": False,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"output": "", "error": "Command timed out after 30 seconds.",
                    "blocked": False, "needs_confirm": False}
        except Exception as e:
            log.error(f"CMD error: {e}")
            return {"output": "", "error": str(e), "blocked": False, "needs_confirm": False}

    def run_powershell(self, script: str) -> dict:
        """Run a PowerShell script string."""
        return self.run(f'powershell -Command "{script}"')

    def change_dir(self, path: str) -> str:
        """Change working directory for subsequent commands."""
        p = Path(path)
        if p.is_dir():
            self.cwd = str(p)
            return f"Working directory set to {self.cwd}"
        return f"Directory not found: {path}"
