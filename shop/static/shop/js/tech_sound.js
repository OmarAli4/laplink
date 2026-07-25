// Lap Link Tech Audio Synthesizer (Zero-dependency Web Audio API)
const TechSound = {
    // Default enabled unless explicitly disabled by user
    enabled: localStorage.getItem('laplink_sound_enabled') !== 'false',
    ctx: null,

    init() {
        if (!this.ctx && (window.AudioContext || window.webkitAudioContext)) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            this.ctx = new AudioCtx();
        }
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    },

    toggle() {
        this.enabled = !this.enabled;
        localStorage.setItem('laplink_sound_enabled', this.enabled ? 'true' : 'false');
        if (this.enabled) {
            this.init();
            this.playSuccess();
        }
        return this.enabled;
    },

    lastPlayTime: 0,

    playPop() {
        if (!this.enabled) return;
        
        const nowMs = Date.now();
        if (nowMs - this.lastPlayTime < 100) return;
        this.lastPlayTime = nowMs;

        this.init();
        if (!this.ctx) return;
        
        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            
            osc.type = 'sine';
            osc.frequency.setValueAtTime(600, now);
            osc.frequency.exponentialRampToValueAtTime(1200, now + 0.06);
            
            gain.gain.setValueAtTime(0.15, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.06);
            
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            
            osc.start(now);
            osc.stop(now + 0.06);
        } catch (e) {
            console.error("TechSound error:", e);
        }
    },

    playSuccess() {
        if (!this.enabled) return;
        this.init();
        if (!this.ctx) return;

        try {
            const now = this.ctx.currentTime;
            const osc1 = this.ctx.createOscillator();
            const osc2 = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc1.type = 'sine';
            osc2.type = 'triangle';
            
            osc1.frequency.setValueAtTime(523.25, now);       // C5
            osc1.frequency.setValueAtTime(659.25, now + 0.08); // E5
            osc2.frequency.setValueAtTime(1046.50, now + 0.16); // C6

            gain.gain.setValueAtTime(0.15, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

            osc1.connect(gain);
            osc2.connect(gain);
            gain.connect(this.ctx.destination);

            osc1.start(now);
            osc2.start(now + 0.16);
            osc1.stop(now + 0.25);
            osc2.stop(now + 0.25);
        } catch (e) {
            console.error("TechSound error:", e);
        }
    }
};

// Global click event listener for automatic button sound feedback & audio resume
document.addEventListener('click', (e) => {
    // Resume audio context on first user click
    TechSound.init();

    // Trigger sound on button or interactive elements
    const target = e.target.closest('button, a, input[type="submit"], [role="button"], .btn-shine');
    if (target && TechSound.enabled) {
        TechSound.playPop();
    }
});

// Sound feedback on HTMX form submissions / cart actions
document.addEventListener('htmx:afterOnLoad', () => {
    if (TechSound.enabled) {
        TechSound.playSuccess();
    }
});

window.TechSound = TechSound;
