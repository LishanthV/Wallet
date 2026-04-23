/* ═══════════════════════════════════════════════
   NexWallet — main.js
   Premium Unified Logic (Module Pattern)
   ═══════════════════════════════════════════════ */

const NexWallet = (function() {
    // Private selectors
    const SELECTORS = {
        flash: '.flash-message',
        strengthFill: 'strengthFill',
        strengthLabel: 'strengthLabel'
    };

    return {
        /**
         * Initialize global UI behaviors
         */
        init: function() {
            this.handleFlashDismissal();
        },

        /**
         * Automatically fades and removes flash messages after 4 seconds
         */
        handleFlashDismissal: function() {
            document.querySelectorAll(SELECTORS.flash).forEach(el => {
                setTimeout(() => {
                    el.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
                    el.style.opacity = '0';
                    el.style.transform = 'translateY(-12px)';
                    setTimeout(() => el.remove(), 600);
                }, 4000);
            });
        },

        /**
         * Toggles password visibility for a given input field
         */
        togglePassword: function(inputId, btn) {
            const input = document.getElementById(inputId);
            if (!input) return;
            
            const isHidden = input.type === 'password';
            input.type = isHidden ? 'text' : 'password';
            
            // Toggle icon/opacity
            btn.style.opacity = isHidden ? '1' : '0.45';
            btn.title = isHidden ? 'Hide password' : 'Show password';
            
            const icon = btn.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-eye', !isHidden);
                icon.classList.toggle('fa-eye-slash', isHidden);
            }
        },

        /**
         * Evaluates and visualizes password strength
         */
        checkStrength: function(value) {
            const fill = document.getElementById(SELECTORS.strengthFill);
            const label = document.getElementById(SELECTORS.strengthLabel);
            if (!fill || !label) return;

            if (!value) {
                fill.style.width = '0%';
                label.textContent = '';
                return;
            }

            let score = 0;
            if (value.length >= 8) score++;
            if (value.length >= 12) score++;
            if (/[A-Z]/.test(value)) score++;
            if (/[0-9]/.test(value)) score++;
            if (/[^A-Za-z0-9]/.test(value)) score++;

            const levels = [
                { pct: '10%', color: '#ef4444', text: 'Weak' },       // Red
                { pct: '25%', color: '#ef4444', text: 'Weak' },       // Red
                { pct: '50%', color: '#f59e0b', text: 'Fair' },       // Orange
                { pct: '75%', color: '#10b981', text: 'Good' },       // Green
                { pct: '100%', color: '#059669', text: 'Strong 💪' }, // Deep Green
            ];

            const lvl = levels[Math.min(score, 4)];
            fill.style.width = lvl.pct;
            fill.style.background = lvl.color;
            label.textContent = lvl.text;
            label.style.color = lvl.color;
        }
    };
})();

// Initialize on load
document.addEventListener('DOMContentLoaded', () => NexWallet.init());
