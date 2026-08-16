"""
AYO AI — Quick Test Script
===========================
Tests the backend starts cleanly without needing Ollama model loaded.
Run: python test_server.py
"""

import sys
import os
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

print("=" * 50)
print("  AYO AI — Backend Test")
print("=" * 50)

# 1. Test all imports
print("\n[1] Testing imports...")
try:
    from backend.core.memory_store import MemoryStore
    from backend.core.tts_engine import TTSEngine
    from backend.api.server import create_app, socketio
    print("    ✅ Core imports OK")
except ImportError as e:
    print(f"    ❌ Import error: {e}")
    sys.exit(1)

# 2. Test memory store
print("\n[2] Testing memory store...")
try:
    memory = MemoryStore()
    memory.add_message("Marshall", "user", "Hello Ayo")
    history = memory.get_history("Marshall")
    print(f"    ✅ Memory store OK — {len(history)} messages")
except Exception as e:
    print(f"    ❌ Memory error: {e}")

# 3. Test TTS engine init
print("\n[3] Testing TTS engine...")
try:
    tts = TTSEngine()
    print("    ✅ TTS engine ready")
except Exception as e:
    print(f"    ⚠️  TTS warning: {e}")

# 4. Test Flask app creation (no brain needed for basic routes)
print("\n[4] Testing Flask API server creation...")
try:
    app = create_app(brain=None, memory=memory, tts=None, verifier=None, enroller=None)
    print("    ✅ Flask app created OK")

    # Start test server
    import requests
    def run_server():
        socketio.run(app, host="127.0.0.1", port=5051, debug=False, log_output=False)

    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(2)

    resp = requests.get("http://localhost:5051/api/status", timeout=3)
    print(f"    ✅ API /status: {resp.status_code} → {resp.json()}")

except Exception as e:
    print(f"    ❌ Server error: {e}")

print("\n" + "=" * 50)
print("  Test complete! Run 'npm start' to launch the app.")
print("=" * 50)
