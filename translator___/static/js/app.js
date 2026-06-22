'use strict';

const srcText    = document.getElementById('srcText');
const srcLang    = document.getElementById('srcLang');
const tgtLang    = document.getElementById('tgtLang');
const swapBtn    = document.getElementById('swapBtn');
const translateBtn = document.getElementById('translateBtn');
const outputArea = document.getElementById('outputArea');
const charCount  = document.getElementById('charCount');
const clearBtn   = document.getElementById('clearBtn');
const copyBtn    = document.getElementById('copyBtn');
const srcTtsBtn  = document.getElementById('srcTtsBtn');
const tgtTtsBtn  = document.getElementById('tgtTtsBtn');
const statusBadge = document.getElementById('statusBadge');
const tgtLabel   = document.getElementById('tgtLabel');
const btnLabel   = document.getElementById('btnLabel');
const toast      = document.getElementById('toast');
const chipRow    = document.getElementById('chipRow');
const historyList = document.getElementById('historyList');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');

let translatedText = '';
let isBusy = false;
let history = [];

const MAX_HISTORY = 12;

// ── floating particles background ──────────────────────────────────────────
(function initParticles() {
  const container = document.getElementById('particles');
  if (!container) return;
  const count = 22;
  for (let i = 0; i < count; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    const left = Math.random() * 100;
    const delay = Math.random() * 18;
    const duration = 14 + Math.random() * 14;
    const size = 1.5 + Math.random() * 2.5;
    p.style.left = `${left}%`;
    p.style.bottom = '-10px';
    p.style.width = `${size}px`;
    p.style.height = `${size}px`;
    p.style.animationDelay = `${delay}s`;
    p.style.animationDuration = `${duration}s`;
    container.appendChild(p);
  }
})();

// ── character counter ──────────────────────────────────────────────────────
srcText.addEventListener('input', () => {
  const len = srcText.value.length;
  charCount.textContent = `${len} / 5000`;
  translateBtn.disabled = len === 0 || isBusy;
  srcTtsBtn.style.display = len > 0 ? 'flex' : 'none';
});

// ── clear ──────────────────────────────────────────────────────────────────
clearBtn.addEventListener('click', () => {
  srcText.value = '';
  srcText.dispatchEvent(new Event('input'));
  resetOutput();
});

// ── swap ───────────────────────────────────────────────────────────────────
swapBtn.addEventListener('click', () => {
  if (srcLang.value === 'Auto-detect') return;

  swapBtn.classList.add('spin');
  setTimeout(() => swapBtn.classList.remove('spin'), 350);

  const tmp = srcLang.value;
  srcLang.value = tgtLang.value;
  if ([...tgtLang.options].some(o => o.value === tmp)) {
    tgtLang.value = tmp;
  } else {
    tgtLang.selectedIndex = 0;
  }
  syncActiveChip();

  if (translatedText) {
    srcText.value = translatedText;
    srcText.dispatchEvent(new Event('input'));
    resetOutput();
  }
});

// ── quick language chips ─────────────────────────────────────────────────
function syncActiveChip() {
  [...chipRow.children].forEach(chip => {
    chip.classList.toggle('active', chip.dataset.lang === tgtLang.value);
  });
}

chipRow.addEventListener('click', (e) => {
  const chip = e.target.closest('.lang-chip');
  if (!chip) return;
  const lang = chip.dataset.lang;
  if ([...tgtLang.options].some(o => o.value === lang)) {
    tgtLang.value = lang;
    syncActiveChip();
    if (srcText.value.trim()) doTranslate();
  }
});

tgtLang.addEventListener('change', syncActiveChip);
syncActiveChip();

// ── translate ──────────────────────────────────────────────────────────────
translateBtn.addEventListener('click', doTranslate);

srcText.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    if (!translateBtn.disabled) doTranslate();
  }
});

async function doTranslate() {
  const text = srcText.value.trim();
  if (!text || isBusy) return;

  isBusy = true;
  translateBtn.disabled = true;
  btnLabel.textContent = 'Translating…';
  tgtLabel.textContent = `Decoded Output — ${tgtLang.value} ⟩`;
  setStatus('translating', 'Translating');

  outputArea.innerHTML = '<span class="placeholder translating-dots">Translating</span>';
  copyBtn.style.display = 'none';
  tgtTtsBtn.style.display = 'none';
  translatedText = '';

  try {
    const res = await fetch('/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        source_language: srcLang.value,
        target_language: tgtLang.value,
      }),
    });

    const data = await res.json();

    if (!res.ok || data.error) {
      setStatus('error', 'Error');
      outputArea.innerHTML = `<span class="placeholder" style="color:var(--error-text)">${data.error || 'Something went wrong.'}</span>`;
    } else {
      translatedText = data.translation;
      outputArea.textContent = translatedText;
      setStatus('done', 'Done');
      copyBtn.style.display = 'flex';
      tgtTtsBtn.style.display = 'flex';
      addToHistory(text, translatedText, srcLang.value, tgtLang.value);
    }
  } catch {
    setStatus('error', 'Error');
    outputArea.innerHTML = '<span class="placeholder" style="color:var(--error-text)">Network error. Is the server running?</span>';
  }

  isBusy = false;
  btnLabel.textContent = 'Translate';
  translateBtn.disabled = srcText.value.length === 0;
}

// ── copy ───────────────────────────────────────────────────────────────────
copyBtn.addEventListener('click', () => {
  if (!translatedText) return;
  navigator.clipboard.writeText(translatedText).then(() => showToast('Copied to clipboard'));
});

// ── text-to-speech ─────────────────────────────────────────────────────────
srcTtsBtn.addEventListener('click', () => speak(srcText.value));
tgtTtsBtn.addEventListener('click', () => speak(translatedText));

function speak(text) {
  if (!window.speechSynthesis || !text) return;
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(text);
  window.speechSynthesis.speak(utt);
}

// ── translation history ──────────────────────────────────────────────────
function addToHistory(srcTxt, tgtTxt, srcL, tgtL) {
  history.unshift({ srcTxt, tgtTxt, srcL, tgtL, ts: Date.now() });
  if (history.length > MAX_HISTORY) history = history.slice(0, MAX_HISTORY);
  renderHistory();
}

function renderHistory() {
  if (history.length === 0) {
    historyList.innerHTML = '<div class="history-empty">No translations yet — your history will appear here</div>';
    return;
  }

  historyList.innerHTML = history.map((h, i) => `
    <div class="history-item" data-index="${i}">
      <div class="history-meta">
        <svg width="11" height="11" viewBox="0 0 14 14" fill="none"><path d="M2 6h10M9 3l3 3-3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        ${escapeHtml(h.srcL)} → ${escapeHtml(h.tgtL)}
      </div>
      <div class="history-text">
        <span class="history-src">${escapeHtml(truncate(h.srcTxt, 80))}</span>
        <span class="history-tgt">${escapeHtml(truncate(h.tgtTxt, 80))}</span>
      </div>
    </div>
  `).join('');
}

historyList.addEventListener('click', (e) => {
  const item = e.target.closest('.history-item');
  if (!item) return;
  const idx = parseInt(item.dataset.index, 10);
  const h = history[idx];
  if (!h) return;

  srcLang.value = [...srcLang.options].some(o => o.value === h.srcL) ? h.srcL : 'Auto-detect';
  if ([...tgtLang.options].some(o => o.value === h.tgtL)) tgtLang.value = h.tgtL;
  syncActiveChip();

  srcText.value = h.srcTxt;
  srcText.dispatchEvent(new Event('input'));

  translatedText = h.tgtTxt;
  outputArea.textContent = h.tgtTxt;
  tgtLabel.textContent = `Decoded Output — ${h.tgtL} ⟩`;
  setStatus('done', 'Done');
  copyBtn.style.display = 'flex';
  tgtTtsBtn.style.display = 'flex';
});

clearHistoryBtn.addEventListener('click', () => {
  history = [];
  renderHistory();
});

function truncate(s, n) {
  return s.length > n ? s.slice(0, n).trim() + '…' : s;
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

// ── helpers ────────────────────────────────────────────────────────────────
function resetOutput() {
  translatedText = '';
  outputArea.innerHTML = '<span class="placeholder">Translation will appear here</span>';
  copyBtn.style.display = 'none';
  tgtTtsBtn.style.display = 'none';
  statusBadge.style.display = 'none';
  tgtLabel.textContent = 'Decoded Output ⟩';
}

function setStatus(type, label) {
  statusBadge.style.display = 'inline';
  statusBadge.className = `status-badge status-${type}`;
  statusBadge.textContent = label;
}

let toastTimer;
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2200);
}
