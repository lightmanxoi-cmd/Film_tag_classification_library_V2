/**
 * 会话管理模块
 */

const SESSION_TIMEOUT = 3 * 60 * 60 * 1000;
const WARNING_THRESHOLD = 60000;
const DANGER_THRESHOLD = 180000;

class SessionManager {
    constructor() {
        this.lastActivityTime = Date.now();
        this.timerInterval = null;
        this.warningShown = false;
        this.onTimeout = null;
        this.onWarning = null;
        this.onTimerUpdate = null;
        this.isPaused = false;
        this.pausedTime = 0;
        this.videoCheckInterval = null;
    }

    init(options = {}) {
        this.onTimeout = options.onTimeout || this._defaultTimeout;
        this.onWarning = options.onWarning || this._defaultWarning;
        this.onTimerUpdate = options.onTimerUpdate || null;
        this.pauseOnVideoPlay = options.pauseOnVideoPlay !== false;

        this._bindActivityEvents();
        this.timerInterval = setInterval(() => this._checkTimeout(), 1000);
        this._updateTimerDisplay();

        if (this.pauseOnVideoPlay) {
            this._startVideoPlaybackCheck();
        }
    }

    _bindActivityEvents() {
        const events = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
        events.forEach(event => {
            document.addEventListener(event, () => this._handleActivity(), { passive: true });
        });
    }

    _handleActivity() {
        if (!this.isPaused) {
            this.lastActivityTime = Date.now();
            this.warningShown = false;
        }
    }

    _checkTimeout() {
        if (this.isPaused) {
            this.lastActivityTime = Date.now() - this.pausedTime;
            this._updateTimerDisplay();
            return;
        }

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
        const elapsed = Date.now() - this.lastActivityTime;
        const remaining = Math.max(0, SESSION_TIMEOUT - elapsed);
        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);

        const timerEl = document.getElementById('sessionTimer');
        if (timerEl) {
            timerEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

            timerEl.classList.remove('warning', 'danger', 'paused');
            if (this.isPaused) {
                timerEl.classList.add('paused');
            } else if (remaining <= WARNING_THRESHOLD) {
                timerEl.classList.add('danger');
            } else if (remaining <= DANGER_THRESHOLD) {
                timerEl.classList.add('warning');
            }
        }

        if (this.onTimerUpdate) {
            let status = 'normal';
            if (this.isPaused) {
                status = 'paused';
            } else if (remaining <= WARNING_THRESHOLD) {
                status = 'danger';
            } else if (remaining <= DANGER_THRESHOLD) {
                status = 'warning';
            }

            this.onTimerUpdate({
                minutes,
                seconds,
                remaining,
                status,
                formatted: `${minutes}:${seconds.toString().padStart(2, '0')}`,
                isPaused: this.isPaused
            });
        }
    }

    _startVideoPlaybackCheck() {
        this.videoCheckInterval = setInterval(() => {
            const isPlaying = this._isAnyVideoPlaying();
            if (isPlaying && !this.isPaused) {
                this.pause();
            } else if (!isPlaying && this.isPaused) {
                this.resume();
            }
        }, 1000);
    }

    _isAnyVideoPlaying() {
        const videos = document.querySelectorAll('video');
        for (const video of videos) {
            if (!video.paused && !video.ended && video.currentTime > 0) {
                return true;
            }
        }
        return false;
    }

    pause() {
        if (!this.isPaused) {
            this.isPaused = true;
            this.pausedTime = Date.now() - this.lastActivityTime;
            console.log('[SessionManager] 会话倒计时已暂停（视频播放中）');
        }
    }

    resume() {
        if (this.isPaused) {
            this.isPaused = false;
            this.lastActivityTime = Date.now() - this.pausedTime;
            this.pausedTime = 0;
            this.warningShown = false;
            console.log('[SessionManager] 会话倒计时已恢复');
        }
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
        if (this.videoCheckInterval) {
            clearInterval(this.videoCheckInterval);
            this.videoCheckInterval = null;
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
