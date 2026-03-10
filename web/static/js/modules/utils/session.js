/**
 * 会话管理模块
 */

const SESSION_TIMEOUT = 10 * 60 * 1000;
const WARNING_THRESHOLD = 60000;
const DANGER_THRESHOLD = 180000;

class SessionManager {
    constructor() {
        this.lastActivityTime = Date.now();
        this.timerInterval = null;
        this.warningShown = false;
        this.onTimeout = null;
        this.onWarning = null;
    }

    init(options = {}) {
        this.onTimeout = options.onTimeout || this._defaultTimeout;
        this.onWarning = options.onWarning || this._defaultWarning;
        this.onTimerUpdate = options.onTimerUpdate || null;
        
        this._bindActivityEvents();
        this.timerInterval = setInterval(() => this._checkTimeout(), 1000);
        this._updateTimerDisplay();
    }

    _bindActivityEvents() {
        const events = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
        events.forEach(event => {
            document.addEventListener(event, () => this._handleActivity(), { passive: true });
        });
    }

    _handleActivity() {
        this.lastActivityTime = Date.now();
        this.warningShown = false;
    }

    _checkTimeout() {
        const elapsed = Date.now() - this.lastActivityTime;
        const remaining = SESSION_TIMEOUT - elapsed;
        
        this._updateTimerDisplay();
        
        if (remaining <= WARNING_THRESHOLD && remaining > 30000 && !this.warningShown) {
            this.onWarning(Math.ceil(remaining / 1000));
            this.warningShown = true;
        }
        
        if (remaining <= 0) {
            this.destroy();
            this.onTimeout();
        }
    }

    _updateTimerDisplay() {
        if (!this.onTimerUpdate) return;
        
        const elapsed = Date.now() - this.lastActivityTime;
        const remaining = Math.max(0, SESSION_TIMEOUT - elapsed);
        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);
        
        let status = 'normal';
        if (remaining <= WARNING_THRESHOLD) {
            status = 'danger';
        } else if (remaining <= DANGER_THRESHOLD) {
            status = 'warning';
        }
        
        this.onTimerUpdate({
            minutes,
            seconds,
            remaining,
            status,
            formatted: `${minutes}:${seconds.toString().padStart(2, '0')}`
        });
    }

    _defaultTimeout() {
        alert('由于长时间未操作，您已自动退出登录');
        window.location.href = '/logout';
    }

    _defaultWarning(seconds) {
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        console.log(`会话将在 ${minutes}分${secs}秒 后过期`);
    }

    destroy() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    getRemainingTime() {
        const elapsed = Date.now() - this.lastActivityTime;
        return Math.max(0, SESSION_TIMEOUT - elapsed);
    }

    isActive() {
        return this.getRemainingTime() > 0;
    }
}

export const sessionManager = new SessionManager();

export function initSessionTimeout(options) {
    sessionManager.init(options);
    return sessionManager;
}
