/**
 * AYO AI — Dashboard Frontend Logic
 * ===================================
 * Handles: page navigation, WebSocket, chat UI, voice orb, phone controls,
 *          voice enrollment, document management, settings.
 */

const API_URL = "http://localhost:5050";
let socket    = null;
let apiBase   = API_URL;

// ── Init ──────────────────────────────────────────────────────────────────────

(async function init() {
  // If running in Electron, get the real API URL
  if (window.ayoElectron) {
    apiBase = await window.ayoElectron.getApiUrl();
    setupTitlebarControls();
  }

  setupNavigation();
  setupChat();
  setupPhonePage();
  setupVoicePage();
  setupDocsPage();
  connectSocket();
  checkStatus();
  setInterval(checkStatus, 10000);
})();

// ── Socket ────────────────────────────────────────────────────────────────────

function connectSocket() {
  try {
    socket = io(apiBase, { transports: ["websocket", "polling"] });

    socket.on("connect", () => {
      console.log("🔌 Connected to Ayo backend");
      setStatus("Ayo is ready", true);
    });

    socket.on("disconnect", () => setStatus("Disconnected", false));

    socket.on("ayo_listening", (data) => {
      setOrbState("listening");
      showOrbLabel(`Listening… (${data.speaker})`);
    });

    socket.on("user_message", (data) => {
      addMessage(data.text, "user", data.speaker);
      setOrbState("thinking");
    });

    socket.on("ayo_response", (data) => {
      addMessage(data.text, "ayo");
      setOrbState("idle");
    });

  } catch (e) {
    console.warn("Socket connection failed — running in standalone mode.");
  }
}

// ── Status ────────────────────────────────────────────────────────────────────

async function checkStatus() {
  try {
    const res  = await fetch(`${apiBase}/api/status`, { signal: AbortSignal.timeout(3000) });
    const data = await res.json();
    setStatus("Ayo is ready", true);
    document.getElementById("modelName").textContent = data.model || "Ollama";
    hideOfflineBanner();
    // Also fetch available models for the settings dropdown
    loadAvailableModels();
  } catch {
    setStatus("Backend offline", false);
    showOfflineBanner();
  }
}

function showOfflineBanner() {
  let banner = document.getElementById("offlineBanner");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "offlineBanner";
    banner.style.cssText = `
      position: fixed; top: 38px; left: 0; right: 0; z-index: 900;
      background: rgba(239,68,68,0.15); border-bottom: 1px solid rgba(239,68,68,0.3);
      color: #EF4444; text-align: center; padding: 8px 16px; font-size: 0.82rem;
      font-weight: 500; display: flex; align-items: center; justify-content: center; gap: 8px;
    `;
    banner.innerHTML = `
      <span>Backend offline — run <code style="background:rgba(0,0,0,0.3);padding:2px 6px;border-radius:4px">python main.py --no-enroll</code> to start Ayo</span>
      <button onclick="checkStatus()" style="background:rgba(239,68,68,0.2);border:1px solid rgba(239,68,68,0.4);color:#EF4444;padding:2px 10px;border-radius:6px;cursor:pointer;font-size:0.8rem">Retry</button>
    `;
    document.body.appendChild(banner);
  }
  banner.style.display = "flex";
}

function hideOfflineBanner() {
  const banner = document.getElementById("offlineBanner");
  if (banner) banner.style.display = "none";
}

async function loadAvailableModels() {
  try {
    const res = await fetch(`${apiBase}/api/models`, { signal: AbortSignal.timeout(3000) });
    const data = await res.json();
    const select = document.getElementById("ollamaModel");
    if (data.models && data.models.length > 0) {
      select.innerHTML = data.models.map(m =>
        `<option value="${m}" ${m === data.active ? 'selected' : ''}>${m}</option>`
      ).join("");
    }
  } catch {}
}

function setStatus(text, online) {
  const badge = document.getElementById("statusBadge");
  const dot   = badge.querySelector(".status-dot");
  document.getElementById("statusText").textContent = text;
  badge.style.background = online ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.12)";
  badge.style.borderColor = online ? "rgba(16,185,129,0.25)" : "rgba(239,68,68,0.25)";
  badge.style.color = online ? "#10B981" : "#EF4444";
  dot.style.background = online ? "#10B981" : "#EF4444";
}

// ── Navigation ────────────────────────────────────────────────────────────────

function setupNavigation() {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const page = btn.dataset.page;
      document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`page-${page}`).classList.add("active");

      // Load data for relevant pages
      if (page === "voices") loadUsers();
      if (page === "docs")   loadDocuments();
      if (page === "phone")  refreshPhoneStatus();
    });
  });
}

// ── Titlebar ──────────────────────────────────────────────────────────────────

function setupTitlebarControls() {
  document.getElementById("btnMin")?.addEventListener("click", () => window.ayoElectron.minimize());
  document.getElementById("btnMax")?.addEventListener("click", () => window.ayoElectron.maximize());
  document.getElementById("btnClose")?.addEventListener("click", () => window.ayoElectron.hide());
}

// ── Chat ──────────────────────────────────────────────────────────────────────

function setupChat() {
  const input   = document.getElementById("textInput");
  const sendBtn = document.getElementById("sendBtn");

  const send = () => {
    const text = input.value.trim();
    if (!text) return;
    sendCommand(text);
    input.value = "";
    input.style.height = "auto";
  };

  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  });

  // Quick action buttons
  document.querySelectorAll(".qa-btn").forEach(btn => {
    btn.addEventListener("click", () => sendCommand(btn.dataset.cmd));
  });

  // Voice orb click = activate listening
  document.getElementById("voiceOrb").addEventListener("click", () => {
    toast("Say your command now…");
    setOrbState("listening");
    showOrbLabel("Listening…");
  });
}

async function sendCommand(text, speaker = "Marshall") {
  addMessage(text, "user", speaker);
  setOrbState("thinking");

  try {
    const res  = await fetch(`${apiBase}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, speaker }),
    });
    const data = await res.json();
    addMessage(data.text || "I couldn't process that.", "ayo");
  } catch (e) {
    addMessage("I'm having trouble reaching my backend. Is Python running?", "ayo");
  } finally {
    setOrbState("idle");
  }
}

function addMessage(text, role, speaker = "Ayo") {
  const msgs  = document.getElementById("chatMessages");
  const isAyo = role === "ayo";
  const div   = document.createElement("div");
  div.className = `message ${isAyo ? "ayo-msg" : "user-msg"}`;

  const now   = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const init  = isAyo ? "A" : (speaker?.[0]?.toUpperCase() || "U");

  // Format text with markdown-lite
  const formatted = text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, `<code style="font-family:monospace;background:rgba(0,0,0,0.3);padding:1px 5px;border-radius:4px">$1</code>`)
    .replace(/\n/g, "<br>");

  div.innerHTML = `
    <div class="msg-avatar">${init}</div>
    <div class="msg-bubble">
      <p>${formatted}</p>
      <span class="msg-time">${now}</span>
    </div>`;

  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

// ── Orb State ─────────────────────────────────────────────────────────────────

function setOrbState(state) {
  const orb   = document.getElementById("voiceOrb");
  const label = document.getElementById("orbLabel");
  orb.className = "orb";
  if (state === "listening") {
    orb.classList.add("listening");
    label.textContent = "Listening…";
  } else if (state === "thinking") {
    label.textContent = "Thinking…";
  } else {
    label.textContent = 'Listening for "Ayo"…';
  }
}

function showOrbLabel(text) {
  document.getElementById("orbLabel").textContent = text;
}

// ── Voice Profiles ────────────────────────────────────────────────────────────

function setupVoicePage() {
  document.getElementById("enrollBtn").addEventListener("click", startEnrollment);
}

async function loadUsers() {
  try {
    const res   = await fetch(`${apiBase}/api/users`);
    const users = await res.json();
    const list  = document.getElementById("userList");

    if (!users.length) {
      list.innerHTML = '<div class="loading-text">No users enrolled yet.</div>';
      return;
    }

    list.innerHTML = users.map(u => `
      <div class="user-item">
        <div class="user-info">
          <span class="user-name">👤 ${u.name}</span>
          <span class="user-samples">${u.samples} voice samples</span>
        </div>
        <button class="del-btn" data-name="${u.name}">Revoke</button>
      </div>
    `).join("");

    list.querySelectorAll(".del-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!confirm(`Remove voice access for ${btn.dataset.name}?`)) return;
        await fetch(`${apiBase}/api/users/${btn.dataset.name}`, { method: "DELETE" });
        loadUsers();
        toast(`${btn.dataset.name}'s access removed.`);
      });
    });
  } catch {
    document.getElementById("userList").innerHTML = '<div class="loading-text">Could not load users.</div>';
  }
}

async function startEnrollment() {
  const name = document.getElementById("enrollName").value.trim();
  if (!name) { toast("Please enter a name first."); return; }

  toast(`Starting enrollment for ${name}…`);
  await sendCommand(`Ayo, register this voice as ${name}`);
  setTimeout(loadUsers, 3000);
}

// ── Phone ─────────────────────────────────────────────────────────────────────

function setupPhonePage() {
  document.getElementById("connectPhoneBtn").addEventListener("click", async () => {
    const ip = document.getElementById("phoneIp").value.trim();
    if (!ip) { toast("Please enter the phone IP address."); return; }
    const res = await fetch(`${apiBase}/api/phone/connect`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ip }),
    });
    const data = await res.json();
    toast(data.message || "Connected!");
    refreshPhoneStatus();
  });

  document.querySelectorAll(".ctrl-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      sendCommand(`Phone: ${action.replace("_", " ")}`);
    });
  });
}

async function refreshPhoneStatus() {
  try {
    const res  = await fetch(`${apiBase}/api/phone/status`);
    const data = await res.json();
    const conn = document.getElementById("phoneConnected");
    conn.textContent  = data.connected ? "Online" : "Offline";
    conn.className    = `badge ${data.connected ? "badge-on" : "badge-off"}`;
    document.getElementById("phoneBattery").textContent = data.battery || "—";
    document.getElementById("phoneIpDisplay").textContent = data.ip || "—";
  } catch {}
}

// ── Documents ─────────────────────────────────────────────────────────────────

function setupDocsPage() {
  document.getElementById("createPdfBtn").addEventListener("click", async () => {
    const topic = document.getElementById("pdfTopic").value.trim();
    const content = document.getElementById("pdfContent").value.trim();
    if (!topic) { toast("Please enter a topic."); return; }
    toast(`Generating PDF: ${topic}…`);
    await sendCommand(`Create a PDF about "${topic}"${content ? ` with this content: ${content}` : ""}`);
    setTimeout(loadDocuments, 3000);
  });

  document.getElementById("createPptBtn").addEventListener("click", async () => {
    const topic = document.getElementById("pptTopic").value.trim();
    const content = document.getElementById("pptContent").value.trim();
    if (!topic) { toast("Please enter a topic."); return; }
    toast(`Generating PowerPoint: ${topic}…`);
    await sendCommand(`Create a PowerPoint presentation about "${topic}"${content ? ` with slides: ${content}` : ""}`);
    setTimeout(loadDocuments, 3000);
  });

  document.getElementById("vibeCodeBtn").addEventListener("click", async () => {
    const desc = document.getElementById("codeDesc").value.trim();
    const lang = document.getElementById("codeLang").value;
    if (!desc) { toast("Please describe what to build."); return; }
    toast(`Generating ${lang} code…`);
    await sendCommand(`Write ${lang} code for: ${desc}`);
    setTimeout(loadDocuments, 3000);
  });
}

async function loadDocuments() {
  try {
    const res  = await fetch(`${apiBase}/api/documents`);
    const docs = await res.json();
    const list = document.getElementById("docList");

    if (!docs.length) { list.innerHTML = '<div class="loading-text">No documents yet.</div>'; return; }

    const icons = { pdf: "📄", pptx: "📊", html: "🌐", py: "🐍", js: "⚡", txt: "📝" };
    list.innerHTML = docs.map(d => {
      const ext  = d.name.split(".").pop();
      const icon = icons[ext] || "📁";
      const size = (d.size / 1024).toFixed(1) + " KB";
      return `<div class="doc-item" data-path="${d.path}">
        <span class="doc-icon">${icon}</span>
        <div>
          <div class="doc-name">${d.name}</div>
          <div class="doc-size">${size}</div>
        </div>
      </div>`;
    }).join("");

    list.querySelectorAll(".doc-item").forEach(item => {
      item.addEventListener("click", () => {
        sendCommand(`Open the file at ${item.dataset.path}`);
      });
    });
  } catch {
    document.getElementById("docList").innerHTML = '<div class="loading-text">Could not load documents.</div>';
  }
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function toast(message) {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = message;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}
