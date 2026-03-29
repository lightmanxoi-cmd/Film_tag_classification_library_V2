/**
 * 会话管理模块
 * 
 * 登录状态永久有效，不会因超时而登出
 */

const SESSION_TIMEOUT = Infinity;
const WARNING_THRESHOLD = Infinity;
const DANGER_THRESHOLD = Infinity;

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
        const timerEl = document.getElementById('sessionTimer');
        if (timerEl) {
            timerEl.textContent = '∞';
            timerEl.classList.remove('warning', 'danger', 'paused');
        }

        if (this.onTimerUpdate) {
            this.onTimerUpdate({
                minutes: Infinity,
                seconds: 0,
                remaining: Infinity,
                status: 'permanent',
                formatted: '∞',
                isPaused: false
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
        // 登录状态永久有效，不会自动登出
        console.log('[SessionManager] 会话永久有效');
    }

    _defaultWarning(seconds) {
        // 登录状态永久有效，不会显示警告
        console.log('[SessionManager] 会话永久有效');
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
        return Infinity;
    }

    isActive() {
        return true;
    }
}

export const sessionManager = new SessionManager();

export function initSessionTimeout(options) {
    sessionManager.init(options);
    return sessionManager;
}
