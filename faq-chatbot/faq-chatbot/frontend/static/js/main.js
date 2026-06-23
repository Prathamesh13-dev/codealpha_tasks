/* ════════════════════════════════════════════════════════════════════════
   FAQ Chatbot — Frontend JS
   ════════════════════════════════════════════════════════════════════════ */

const API = "http://127.0.0.1:5000";

// ── DOM refs ──────────────────────────────────────────────────────────────────
const messagesEl       = document.getElementById("messages");
const userInputEl      = document.getElementById("userInput");
const sendBtnEl        = document.getElementById("sendBtn");
const faqListEl        = document.getElementById("faqList");
const faqSearchEl      = document.getElementById("faqSearch");
const suggestionsEl    = document.getElementById("suggestions");
const clearBtnEl       = document.getElementById("clearBtn");
const sidebarEl        = document.getElementById("sidebar");
const sidebarToggleEl  = document.getElementById("sidebarToggle");
const sidebarToggleMEl = document.getElementById("sidebarToggleMobile");
const statusLineEl     = document.getElementById("statusLine");

// ── State ─────────────────────────────────────────────────────────────────────
let allFaqs     = [];
let isWaiting   = false;
let msgCount    = 0;

// ════════════════════════════════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════════════════════════════════
window.addEventListener("DOMContentLoaded", () => {
  renderWelcome();
  loadFaqs();
  bindEvents();
  userInputEl.focus();
});

// ════════════════════════════════════════════════════════════════════════════
//  FAQ SIDEBAR
// ════════════════════════════════════════════════════════════════════════════
async function loadFaqs() {
  try {
    const res  = await fetch(`${API}/api/faqs`);
    allFaqs    = await res.json();
    statusLineEl.textContent = `NLP-powered · ${allFaqs.length} FAQs loaded`;
    renderFaqList(allFaqs);
  } catch {
    faqListEl.innerHTML = `<div class="faq-loading" style="color:#ff5a5a">⚠ Could not connect to backend.</div>`;
  }
}

function renderFaqList(items) {
  if (!items.length) {
    faqListEl.innerHTML = `<div class="faq-loading">No FAQs match.</div>`;
    return;
  }

  // Group by category (question objects have no category in /api/faqs; just list)
  faqListEl.innerHTML = items.map(faq => `
    <button class="faq-item" data-q="${escHtml(faq.question)}">${escHtml(faq.question)}</button>
  `).join("");

  faqListEl.querySelectorAll(".faq-item").forEach(btn => {
    btn.addEventListener("click", () => {
      faqListEl.querySelectorAll(".faq-item").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      sendMessage(btn.dataset.q);
      // Close on mobile
      sidebarEl.classList.remove("mobile-open");
    });
  });
}

faqSearchEl.addEventListener("input", () => {
  const q = faqSearchEl.value.toLowerCase();
  renderFaqList(q ? allFaqs.filter(f => f.question.toLowerCase().includes(q)) : allFaqs);
});

// ════════════════════════════════════════════════════════════════════════════
//  SIDEBAR TOGGLE
// ════════════════════════════════════════════════════════════════════════════
sidebarToggleEl.addEventListener("click", () => {
  sidebarEl.classList.toggle("collapsed");
});
sidebarToggleMEl.addEventListener("click", () => {
  sidebarEl.classList.toggle("mobile-open");
});

// ════════════════════════════════════════════════════════════════════════════
//  EVENTS
// ════════════════════════════════════════════════════════════════════════════
function bindEvents() {
  sendBtnEl.addEventListener("click", submitInput);

  userInputEl.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submitInput(); }
  });

  // Auto-grow textarea
  userInputEl.addEventListener("input", () => {
    userInputEl.style.height = "auto";
    userInputEl.style.height = Math.min(userInputEl.scrollHeight, 120) + "px";
  });

  // Suggestion chips
  suggestionsEl.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => sendMessage(chip.dataset.q));
  });

  clearBtnEl.addEventListener("click", () => {
    messagesEl.innerHTML = "";
    msgCount = 0;
    renderWelcome();
  });
}

function submitInput() {
  const text = userInputEl.value.trim();
  if (!text || isWaiting) return;
  userInputEl.value = "";
  userInputEl.style.height = "auto";
  sendMessage(text);
}

// ════════════════════════════════════════════════════════════════════════════
//  SEND + RECEIVE
// ════════════════════════════════════════════════════════════════════════════
async function sendMessage(text) {
  if (isWaiting) return;
  isWaiting = true;
  sendBtnEl.disabled = true;

  // Remove welcome screen on first real message
  if (msgCount === 0) messagesEl.innerHTML = "";
  msgCount++;

  appendUserMsg(text);
  const typingId = appendTyping();

  try {
    const res  = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    removeTyping(typingId);
    appendBotMsg(data.answer, data.score, data.matched_question);
  } catch (err) {
    removeTyping(typingId);
    appendBotMsg("⚠ Could not reach the server. Make sure `python backend/app.py` is running.", null, null);
  }

  isWaiting = false;
  sendBtnEl.disabled = false;
  userInputEl.focus();
}

// ════════════════════════════════════════════════════════════════════════════
//  RENDER HELPERS
// ════════════════════════════════════════════════════════════════════════════
function renderWelcome() {
  messagesEl.innerHTML = `
    <div class="welcome">
      <div class="welcome-icon">🤖</div>
      <h2>FAQ Assistant</h2>
      <p>Ask me anything about Python, NLP, Machine Learning, Flask, Git, and more.<br>
         Or browse questions in the sidebar.</p>
    </div>`;
}

function appendUserMsg(text) {
  const time = now();
  messagesEl.insertAdjacentHTML("beforeend", `
    <div class="msg user">
      <div class="msg-avatar">👤</div>
      <div class="msg-body">
        <div class="msg-bubble">${escHtml(text)}</div>
        <div class="msg-meta">${time}</div>
      </div>
    </div>`);
  scrollBottom();
}

function appendTyping() {
  const id = `typing-${Date.now()}`;
  messagesEl.insertAdjacentHTML("beforeend", `
    <div class="msg bot" id="${id}">
      <div class="msg-avatar">🤖</div>
      <div class="msg-body">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    </div>`);
  scrollBottom();
  return id;
}

function removeTyping(id) {
  document.getElementById(id)?.remove();
}

function appendBotMsg(answer, score, matched) {
  const time       = now();
  const safeAnswer = formatAnswer(answer);
  let meta         = `<span>${time}</span>`;

  if (score !== null && score !== undefined) {
    const pct   = Math.round(score * 100);
    const cls   = pct >= 60 ? "conf-high" : pct >= 30 ? "conf-mid" : "conf-low";
    const label = pct >= 60 ? "High" : pct >= 30 ? "Medium" : "Low";
    meta += `
      <span class="confidence-bar">
        <span class="conf-dot ${cls}"></span>
        ${label} confidence · ${pct}%
      </span>`;
    if (matched) meta += `<span>matched: "${escHtml(matched)}"</span>`;
  }

  messagesEl.insertAdjacentHTML("beforeend", `
    <div class="msg bot">
      <div class="msg-avatar">🤖</div>
      <div class="msg-body">
        <div class="msg-bubble">${safeAnswer}</div>
        <div class="msg-meta">${meta}</div>
      </div>
    </div>`);
  scrollBottom();
}

// ── Utilities ──────────────────────────────────────────────────────────────
function formatAnswer(text) {
  // Escape HTML, then wrap inline code in <code> tags
  return escHtml(text).replace(/`([^`]+)`/g, "<code>$1</code>");
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function now() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function scrollBottom() {
  messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: "smooth" });
}
