"""
AYO AI — Flask / SocketIO API Server
======================================
Provides REST + WebSocket endpoints for the Electron dashboard.
The dashboard connects here to get live conversation updates and
send commands without going through voice.
"""

import logging
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS

log = logging.getLogger("ayo.api")

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app(brain=None, memory=None, tts=None,
               verifier=None, enroller=None) -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "ayo-ai-secret-2026"
    CORS(app)
    socketio.init_app(app)

    # Store refs in app context
    app.brain    = brain
    app.memory   = memory
    app.tts      = tts
    app.verifier = verifier
    app.enroller = enroller

    # Import here to avoid circular imports
    from backend.tools.dispatcher import ToolDispatcher
    app.dispatcher = ToolDispatcher(brain=brain, memory=memory, tts=tts,
                                    verifier=verifier, enroller=enroller)

    # ── REST Endpoints ────────────────────────────────────────────────────────

    @app.get("/api/status")
    def status():
        return jsonify({
            "status":    "running",
            "model":     brain.model if brain else "none",
            "users":     verifier.list_users() if verifier else [],
            "enrolled":  verifier.enrolled_count() if verifier else 0,
        })

    @app.get("/api/history")
    def history():
        if not memory:
            return jsonify([])
        speaker = request.args.get("speaker")
        return jsonify(memory.get_history(speaker=speaker, limit=50))

    @app.post("/api/chat")
    def chat():
        """Send a text command to Ayo (for dashboard text input)."""
        data    = request.json or {}
        text    = data.get("text", "")
        speaker = data.get("speaker", "User")
        if not text:
            return jsonify({"error": "No text provided"}), 400

        # Graceful degradation — brain not loaded yet
        if not brain:
            msg = "I'm still loading my AI model. Please wait a moment and try again."
            if memory:
                memory.add_message(speaker, "user", text)
                memory.add_message(speaker, "assistant", msg)
            socketio.emit("ayo_response", {"text": msg, "action": None, "params": {}})
            return jsonify({"text": msg, "action": None, "params": {}})

        if memory:
            memory.add_message(speaker, "user", text)

        response = brain.think(text, speaker=speaker,
                               history=memory.get_history(speaker) if memory else None)

        # Execute action if any
        result = ""
        if response.get("action") and hasattr(app, 'dispatcher'):
            result = app.dispatcher.dispatch(
                response["action"], response.get("params", {}), speaker
            )
            if result:
                response["text"] += f"\n\n{result}"

        if tts:
            import threading
            threading.Thread(target=tts.speak, args=(response["text"],), daemon=True).start()

        if memory:
            memory.add_message(speaker, "assistant", response["text"])

        socketio.emit("ayo_response", response)
        return jsonify(response)

    @app.get("/api/models")
    def list_models():
        """List available Ollama models."""
        try:
            import ollama
            models = [m.model for m in ollama.list().models]
            return jsonify({"models": models, "active": brain.model if brain else None})
        except Exception as e:
            return jsonify({"models": [], "active": None, "error": str(e)})

    @app.get("/api/users")
    def list_users():
        if not enroller:
            return jsonify([])
        return jsonify(enroller.list_users())

    @app.delete("/api/users/<name>")
    def delete_user(name: str):
        if enroller and enroller.revoke_user(name):
            return jsonify({"success": True, "message": f"{name} removed."})
        return jsonify({"success": False}), 404

    @app.get("/api/documents")
    def list_documents():
        from pathlib import Path
        docs_dir = Path(__file__).parents[2] / "data" / "documents"
        files = sorted(docs_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        return jsonify([{"name": f.name, "path": str(f), "size": f.stat().st_size}
                        for f in files if f.is_file()][:20])

    @app.post("/api/phone/connect")
    def connect_phone():
        data = request.json or {}
        ip   = data.get("ip", "")
        if not ip:
            return jsonify({"error": "Phone IP required"}), 400
        result = app.dispatcher.phone.connect(ip)
        return jsonify({"message": result})

    @app.get("/api/phone/status")
    def phone_status():
        phone = app.dispatcher.phone
        return jsonify({
            "connected": phone.is_connected(),
            "ip":        phone.ip,
            "battery":   phone.battery_status() if phone.is_connected() else "N/A",
        })

    # ── SocketIO Events ───────────────────────────────────────────────────────

    @socketio.on("connect")
    def on_connect():
        log.info("🔌 Dashboard connected")
        emit("server_ready", {"message": "Ayo AI is ready."})

    @socketio.on("text_command")
    def on_text_command(data):
        """Dashboard sent a typed command."""
        text    = data.get("text", "")
        speaker = data.get("speaker", "User")
        if text and brain:
            response = brain.think(text, speaker=speaker)
            if response.get("action"):
                result = app.dispatcher.dispatch(
                    response["action"], response.get("params", {}), speaker
                )
                if result:
                    response["text"] += f"\n\n{result}"
            emit("ayo_response", response, broadcast=True)
            if tts:
                import threading
                threading.Thread(target=tts.speak,
                                 args=(response["text"],), daemon=True).start()

    return app
