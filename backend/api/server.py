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

    @app.post("/api/enroll/start")
    def enroll_start():
        """Begin an enrollment session for a new user."""
        data = request.json or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "Name is required"}), 400
        # Store name in a session variable
        app._enroll_session = {"name": name, "samples": 0, "required": 5}
        return jsonify({"message": f"Ready to enroll {name}. Record 5 voice samples.",
                        "required": 5, "name": name})

    @app.post("/api/enroll/sample")
    def enroll_sample():
        """Record and submit one voice sample (base64 WAV audio from dashboard)."""
        import base64, io, numpy as np
        if not enroller:
            return jsonify({"error": "Enrollment system not ready"}), 503

        session = getattr(app, "_enroll_session", None)
        if not session:
            return jsonify({"error": "Start enrollment first via /api/enroll/start"}), 400

        data = request.json or {}
        audio_b64 = data.get("audio_b64", "")
        name = session["name"]

        if not audio_b64:
            return jsonify({"error": "No audio data provided"}), 400

        try:
            import soundfile as sf
            raw = base64.b64decode(audio_b64)
            buf = io.BytesIO(raw)
            audio, sr = sf.read(buf)
            # Resample to 16kHz if needed
            if sr != 16000:
                import librosa
                audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
            audio = audio.astype(np.float32)

            result = enroller.add_sample_api(name, audio)
            session["samples"] = result["count"]

            if result["done"]:
                app._enroll_session = None
                socketio.emit("enrollment_complete", {"name": name})

            return jsonify(result)
        except Exception as e:
            log.error(f"Enrollment sample error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.delete("/api/history")
    def clear_history():
        """Clear conversation history for a speaker."""
        speaker = request.args.get("speaker")
        if memory:
            memory.clear_history(speaker)
        return jsonify({"message": "History cleared"})

    @app.get("/api/documents")
    def list_documents():
        from pathlib import Path
        docs_dir = Path(__file__).parents[2] / "data" / "documents"
        docs_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(docs_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        return jsonify([{"name": f.name, "path": str(f), "size": f.stat().st_size}
                        for f in files if f.is_file()][:20])

    @app.post("/api/phone/connect")
    def connect_phone():
        if not hasattr(app, "dispatcher") or not app.dispatcher:
            return jsonify({"message": "Dispatcher not ready — backend still loading"}), 503
        data = request.json or {}
        ip   = data.get("ip", "")
        if not ip:
            return jsonify({"error": "Phone IP required"}), 400
        result = app.dispatcher.phone.connect(ip)
        return jsonify({"message": result})

    @app.get("/api/phone/status")
    def phone_status():
        if not hasattr(app, "dispatcher") or not app.dispatcher:
            return jsonify({"connected": False, "ip": None, "battery": "N/A"})
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
