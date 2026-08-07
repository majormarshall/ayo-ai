"""
AYO AI — Tool Dispatcher
=========================
The action executor. Takes the LLM brain's JSON output and routes
it to the correct tool, then returns a result string.
"""

import logging
from backend.tools.system_control  import (open_app, close_app, take_screenshot,
                                             set_volume, list_files, read_file,
                                             write_file, search_files)
from backend.tools.cmd_runner       import CMDRunner
from backend.tools.phone_bridge     import PhoneBridge
from backend.tools.research_agent   import ResearchAgent
from backend.tools.document_creator import DocumentCreator

log = logging.getLogger("ayo.dispatcher")


class ToolDispatcher:
    def __init__(self, brain=None, memory=None, tts=None,
                 verifier=None, enroller=None):
        self.brain    = brain
        self.memory   = memory
        self.tts      = tts
        self.verifier = verifier
        self.enroller = enroller

        self.cmd      = CMDRunner()
        self.phone    = PhoneBridge()
        self.research = ResearchAgent(brain=brain)
        self.docs     = DocumentCreator()

    # ── Main dispatch ─────────────────────────────────────────────────────────

    def dispatch(self, action: str, params: dict, speaker: str = "User") -> str:
        """Route an action to the correct tool and return result string."""
        if not action:
            return ""

        log.info(f"⚡ Dispatch → {action}({params}) by {speaker}")

        handlers = {
            # System
            "open_app":       lambda p: open_app(p.get("app", "")),
            "close_app":      lambda p: close_app(p.get("app", "")),
            "take_screenshot":lambda p: take_screenshot(p.get("path")),
            "set_volume":     lambda p: set_volume(p.get("level", 50)),
            "list_files":     lambda p: list_files(p.get("directory")),
            "read_file":      lambda p: read_file(p.get("path", "")),
            "write_file":     lambda p: write_file(p.get("path",""), p.get("content","")),
            "search_files":   lambda p: search_files(p.get("query",""), p.get("directory")),

            # CMD
            "run_cmd":        lambda p: self._run_cmd(p),

            # Phone
            "phone_action":   lambda p: self._phone_action(p),
            "connect_phone":  lambda p: self.phone.connect(p.get("ip",""), p.get("port", 5555)),

            # Research
            "web_search":     lambda p: self._search(p),
            "summarise":      lambda p: self.brain.summarise(p.get("text","")) if self.brain else "No brain loaded.",

            # Documents
            "create_pdf":     lambda p: self._create_pdf(p),
            "create_ppt":     lambda p: self._create_ppt(p),
            "vibe_code":      lambda p: self._vibe_code(p),
            "open_document":  lambda p: self.docs.open_document(p.get("path","")),

            # Voice profiles
            "enroll_voice":   lambda p: self._enroll(p, speaker),
            "list_users":     lambda p: self._list_users(),
            "revoke_user":    lambda p: self._revoke(p),
        }

        handler = handlers.get(action)
        if handler:
            try:
                result = handler(params)
                if self.memory:
                    self.memory.log_action(speaker, action, params, str(result)[:200])
                return result or ""
            except Exception as e:
                log.error(f"Tool error ({action}): {e}")
                return f"I ran into a problem with that: {e}"
        else:
            log.warning(f"Unknown action: {action}")
            return f"I don't know how to do '{action}' yet."

    # ── Sub-handlers ──────────────────────────────────────────────────────────

    def _run_cmd(self, p: dict) -> str:
        result = self.cmd.run(p.get("command", ""))
        if result.get("needs_confirm"):
            return f"⚠️ That command needs confirmation: {result['warning']}"
        if result.get("blocked"):
            return result["error"]
        out = result.get("output", "")
        err = result.get("error", "")
        return (out + ("\n" + err if err else "")).strip()

    def _phone_action(self, p: dict) -> str:
        action = p.get("action", "")
        phone  = self.phone
        routes = {
            "open_app":      lambda: phone.open_app(p.get("app","")),
            "close_app":     lambda: phone.close_app(p.get("app","")),
            "call":          lambda: phone.make_call(p.get("number","")),
            "sms":           lambda: phone.send_sms(p.get("number",""), p.get("message","")),
            "volume_up":     lambda: phone.volume_up(p.get("steps", 3)),
            "volume_down":   lambda: phone.volume_down(p.get("steps", 3)),
            "mute":          lambda: phone.mute(),
            "screenshot":    lambda: phone.screenshot(),
            "lock":          lambda: phone.lock_screen(),
            "unlock":        lambda: phone.unlock_screen(),
            "home":          lambda: phone.home(),
            "back":          lambda: phone.back(),
            "battery":       lambda: phone.battery_status(),
            "type":          lambda: phone.type_text(p.get("text","")),
            "tap":           lambda: phone.tap(p.get("x",0), p.get("y",0)),
        }
        fn = routes.get(action)
        return fn() if fn else f"Unknown phone action: {action}"

    def _search(self, p: dict) -> str:
        result = self.research.search(p.get("query",""))
        sources = "\n".join(f"• {s['title']}: {s['url']}" for s in result["sources"][:3])
        return result["summary"] + (f"\n\nSources:\n{sources}" if sources else "")

    def _create_pdf(self, p: dict) -> str:
        path = self.docs.create_pdf(
            topic=p.get("topic", "Document"),
            content=p.get("content", ""),
            filename=p.get("filename"),
        )
        self.docs.open_document(path)
        return f"PDF created and opened: {path}"

    def _create_ppt(self, p: dict) -> str:
        slides = p.get("slides", [])
        if not slides:
            # Auto-generate slide structure from content
            content = p.get("content", "")
            slides  = [{"title": "Overview", "content": content}]
        path = self.docs.create_ppt(
            topic=p.get("topic", "Presentation"),
            slides=slides,
            filename=p.get("filename"),
        )
        self.docs.open_document(path)
        return f"PowerPoint created and opened: {path}"

    def _vibe_code(self, p: dict) -> str:
        code = p.get("code", p.get("content", ""))
        return self.docs.vibe_code(
            description=p.get("description", "code"),
            code=code,
            language=p.get("language", "html"),
        )

    def _enroll(self, p: dict, requester: str) -> str:
        name = p.get("name", "")
        if not name:
            return "Please tell me the name of the person to enroll."
        if self.enroller and self.tts:
            success = self.enroller.enroll_interactive(
                name=name, tts=self.tts, stt=None
            )
            return f"{'Successfully enrolled' if success else 'Enrollment failed for'} {name}."
        return "Enrollment system not ready."

    def _list_users(self) -> str:
        if not self.enroller:
            return "Enrollment system not ready."
        users = self.enroller.list_users()
        if not users:
            return "No users enrolled yet."
        return "Enrolled users:\n" + "\n".join(
            f"• {u['name']} ({u['samples']} samples)" for u in users
        )

    def _revoke(self, p: dict) -> str:
        name = p.get("name", "")
        if self.enroller and self.enroller.revoke_user(name):
            return f"{name}'s voice access has been removed."
        return f"Couldn't find a profile for {name}."
