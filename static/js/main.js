/* ═══════════════════════════════════════════════
   FinanceApp — main.js
   Handles: password toggle, strength meter, flashes
   ═══════════════════════════════════════════════ */

/* ── Password visibility toggle ─────────────── */
function togglePw(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isHidden = input.type === 'password';
  input.type     = isHidden ? 'text' : 'password';
  btn.style.opacity = isHidden ? '1' : '0.45';
  btn.title         = isHidden ? 'Hide password' : 'Show password';
}

/* ── Password strength meter ─────────────────── */
function checkStrength(value) {
  const fill  = document.getElementById('strengthFill');
  const label = document.getElementById('strengthLabel');
  if (!fill || !label) return;

  let score = 0;
  if (value.length >= 8)            score++;
  if (value.length >= 12)           score++;
  if (/[A-Z]/.test(value))          score++;
  if (/[0-9]/.test(value))          score++;
  if (/[^A-Za-z0-9]/.test(value))   score++;

  const levels = [
    { pct: '0%',   color: 'transparent', text: '' },
    { pct: '25%',  color: '#ff5c5c',     text: 'Weak' },
    { pct: '50%',  color: '#ff9800',     text: 'Fair' },
    { pct: '75%',  color: '#8bc34a',     text: 'Good' },
    { pct: '100%', color: '#4caf50',     text: 'Strong 💪' },
  ];
  const lvl = levels[Math.min(score, 4)];
  fill.style.width      = lvl.pct;
  fill.style.background = lvl.color;
  fill.style.boxShadow  = lvl.color !== 'transparent' ? `0 0 8px ${lvl.color}` : 'none';
  label.textContent     = lvl.text;
  label.style.color     = lvl.color;
}

/* ── Flash auto-dismiss (4 s) ────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      el.style.opacity    = '0';
      el.style.transform  = 'translateX(12px)';
      setTimeout(() => el.remove(), 500);
    }, 4000);
  });
});
