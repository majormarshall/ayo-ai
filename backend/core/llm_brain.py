"""
AYO AI — LLM Brain (Ollama)
============================
All AI reasoning goes through here. Talks to a local Ollama instance.
Uses tool-calling to decide what action to take based on user's command.
"""

import json
import logging
from typing import Optional
import ollama

log = logging.getLogger("ayo.brain")

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Ayo, a personal AI assistant that runs on your owner's Windows PC and Android phone.
You are smart, efficient, friendly, and direct. You only respond to authorised users.

When responding, ALWAYS return valid JSON in this format:
{
  "text": "What you say out loud to the user",
  "action": "tool_name_or_null",
  "params": {}
}

Available actions (tools):
- "open_app"         → params: {"app": "notepad"}
- "run_cmd"          → params: {"command": "ipconfig"}
- "web_search"       → params: {"query": "Nigeria news today"}
- "create_pdf"       → params: {"topic": "Climate Change", "content": "..."}
- "create_ppt"       → params: {"topic": "Business Plan", "slides": [...]}
- "vibe_code"        → params: {"description": "a todo list app", "language": "html"}
- "phone_action"     → params: {"action": "open_app", "app": "whatsapp"}
- "take_screenshot"  → params: {}
- "read_file"        → params: {"path": "C:/Users/..."}
- "write_file"       → params: {"path": "...", "content": "..."}
- "set_volume"       → params: {"level": 50}
- "summarise"        → params: {"text": "long text here..."}
- "enroll_voice"     → params: {"name": "John"}
- "list_users"       → params: {}
- "revoke_user"      → params: {"name": "John"}
- null               → just talk, no action needed

Be concise. Never expose raw JSON to the user — the "text" field is what they hear."""

# ── Default Model ─────────────────────────────────────────────────────────────
DEFAULT_MODEL = "llama3.2"   # Falls back to mistral or phi3 if not installed


class LLMBrain:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self._verify_model()
        log.info(f"🧠 LLM Brain ready → model: {self.model}")

    def _verify_model(self):
        """Check Ollama is running and pick best available model. Never blocks."""
        try:
            models = [m.model for m in ollama.list().models]
            # Try preferred models in order
            for candidate in [self.model, "llama3.2", "llama3.2:3b", "mistral", "phi3", "llama3", "gemma2"]:
                if any(candidate in m for m in models):
                    self.model = next(m for m in models if candidate in m)
                    log.info(f"Using model: {self.model}")
                    return
            # No model found — run in degraded mode (don't auto-pull, could take hours)
            log.warning("No Ollama model found. Run: ollama pull llama3.2:3b")
            log.warning("Ayo will respond with a 'loading' message until a model is available.")
            self.model = None
        except Exception as e:
            log.error(f"Ollama not reachable: {e}. Make sure 'ollama serve' is running.")
            self.model = None

    def think(self, user_text: str, speaker: str = "User",
              history: Optional[list] = None) -> dict:
        """
        Send user message to Ollama. Returns structured response dict:
        { "text": str, "action": str|None, "params": dict }
        """
        if not self.model:
            # Try to find a model again in case it finished downloading
            self._verify_model()
        if not self.model:
            return {
                "text": "My AI model is still loading. Run 'ollama pull llama3.2:3b' in a terminal if it's not already downloading.",
                "action": None, "params": {}, "speaker": speaker
            }

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history for context
        if history:
            messages.extend(history[-10:])  # Last 10 turns max

        messages.append({
            "role": "user",
            "content": f"[{speaker}]: {user_text}"
        })

        try:
            result = ollama.chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0.7, "num_predict": 512},
                format="json",
            )
            raw = result.message.content
            parsed = json.loads(raw)

            # Ensure required keys exist
            return {
                "text":   parsed.get("text", "Got it."),
                "action": parsed.get("action", None),
                "params": parsed.get("params", {}),
                "speaker": speaker,
            }

        except json.JSONDecodeError:
            log.error("Brain returned non-JSON. Treating as plain text.")
            text = result.message.content if result else "I couldn't process that."
            return {"text": text, "action": None, "params": {}, "speaker": speaker}

        except Exception as e:
            log.error(f"LLM error: {e}")
            return {
                "text":   "I'm having a brain moment. Please try again.",
                "action": None,
                "params": {},
                "speaker": speaker,
            }

    def summarise(self, text: str) -> str:
        """Summarise a block of text."""
        prompt = f"Summarise the following text in clear, concise bullet points:\n\n{text}"
        try:
            result = ollama.generate(model=self.model, prompt=prompt,
                                     options={"temperature": 0.3, "num_predict": 400})
            return result.response
        except Exception as e:
            log.error(f"Summarise error: {e}")
            return "Could not summarise content."
