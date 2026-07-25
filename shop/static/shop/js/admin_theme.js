/* ==========================================================================
   LAP LINK EXECUTIVE CYBER ADMIN THEME JS - INTERACTIVE MICRO-ANIMATIONS
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Live Animated Clock
    const clockEl = document.getElementById('admin-live-clock');
    if (clockEl) {
        const updateClock = () => {
            const now = new Date();
            clockEl.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        };
        updateClock();
        setInterval(updateClock, 1000);
    }

    // 2. Count-up animation for KPI metric cards
    const animatedNumbers = document.querySelectorAll('.animate-count-up');
    animatedNumbers.forEach(el => {
        const target = parseFloat(el.getAttribute('data-target') || '0');
        const prefix = el.getAttribute('data-prefix') || '';
        const suffix = el.getAttribute('data-suffix') || '';
        const duration = 1200; // ms
        const startTime = performance.now();

        const step = (currentTime) => {
            const progress = Math.min((currentTime - startTime) / duration, 1);
            const easeProgress = 1 - Math.pow(1 - progress, 3); // Ease out cubic
            const currentVal = target * easeProgress;

            if (target % 1 === 0) {
                el.textContent = prefix + Math.round(currentVal).toLocaleString() + suffix;
            } else {
                el.textContent = prefix + currentVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + suffix;
            }

            if (progress < 1) {
                requestAnimationFrame(step);
            }
        };

        requestAnimationFrame(step);
    });
});
