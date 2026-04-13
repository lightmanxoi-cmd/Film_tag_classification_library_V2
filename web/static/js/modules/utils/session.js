/**
 * 会话管理模块
 * 
 * 支持服务端会话超时控制：
 * - 绝对超时：登录后24小时强制失效
 * - 空闲超时：无操作2小时后自动失效
 * - 视频播放时暂停空闲计时
 * - 即将超时时显示警告提示
 */

const INACTIVITY_TIMEOUT = parseInt(document.querySelector('meta[name="inactivity-timeout"]')?.content || '7200') * 1000;
const WARNING_THRESHOLD = 5 * 60 * 1000;
const DANGER_THRESHOLD = 60 * 1000;
const CHECK_INTERVAL = 30000;

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
        this._startTimer();
        
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

    _startTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
        }
        this.timerInterval = setInterval(() => this._checkTimeout(), CHECK_INTERVAL);
        this._checkTimeout();
    }

    _checkTimeout() {
        if (this.isPaused) {
            this.lastActivityTime = Date.now() - this.pausedTime;
            this._updateTimerDisplay();
            return;
        }

        const elapsed = Date.now() - this.lastActivityTime;
        const remaining = INACTIVITY_TIMEOUT - elapsed;

        this._updateTimerDisplay();

        if (remaining <= WARNING_THRESHOLD && remaining > DANGER_THRESHOLD && !this.warningShown) {
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
        if (!timerEl) {
            if (this.onTimerUpdate) {
                this._emitTimerUpdate();
            }
            return;
        }

        const elapsed = Date.now() - this.lastActivityTime;
        const remaining = INACTIVITY_TIMEOUT - elapsed;
        const minutes = Math.max(0, Math.ceil(remaining / 60000));

        if (remaining <= 0) {
            timerEl.textContent = '0:00';
            timerEl.classList.add('danger');
            timerEl.classList.remove('warning', 'paused');
        } else if (this.isPaused) {
            timerEl.textContent = `${minutes}m ⏸`;
            timerEl.classList.add('paused');
            timerEl.classList.remove('warning', 'danger');
        } else if (remaining <= DANGER_THRESHOLD) {
            const secs = Math.ceil(remaining / 1000);
            timerEl.textContent = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`;
            timerEl.classList.add('danger');
            timerEl.classList.remove('warning', 'paused');
        } else if (remaining <= WARNING_THRESHOLD) {
            timerEl.textContent = `${minutes}m`;
            timerEl.classList.add('warning');
            timerEl.classList.remove('danger', 'paused');
        } else {
            timerEl.textContent = `${minutes}m`;
            timerEl.classList.remove('warning', 'danger', 'paused');
        }

        if (this.onTimerUpdate) {
            this._emitTimerUpdate();
        }
    }

    _emitTimerUpdate() {
        const elapsed = Date.now() - this.lastActivityTime;
        const remaining = Math.max(0, INACTIVITY_TIMEOUT - elapsed);
        const totalSeconds = Math.ceil(remaining / 1000);
        this.onTimerUpdate({
            minutes: Math.floor(totalSeconds / 60),
            seconds: totalSeconds % 60,
            remaining: remaining,
            status: this.isPaused ? 'paused' : (remaining <= DANGER_THRESHOLD ? 'danger' : (remaining <= WARNING_THRESHOLD ? 'warning' : 'normal')),
            formatted: this.isPaused ? `${Math.ceil(remaining / 60000)}m ⏸` : `${Math.floor(totalSeconds / 60)}:${String(totalSeconds % 60).padStart(2, '0')}`,
            isPaused: this.isPaused
        });
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
            this._updateTimerDisplay();
        }
    }

    resume() {
        if (this.isPaused) {
            this.isPaused = false;
            this.lastActivityTime = Date.now() - this.pausedTime;
            this.pausedTime = 0;
            this.warningShown = false;
            this._updateTimerDisplay();
        }
    }

    _defaultTimeout() {
        alert('长时间未操作，会话已过期，请重新登录');
        window.location.href = '/login';
    }

    _defaultWarning(seconds) {
        const minutes = Math.ceil(seconds / 60);
        console.warn(`[SessionManager] 会话将在 ${minutes} 分钟后过期，请进行操作以保持登录状态`);
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
        if (this.isPaused) {
            return Math.max(0, INACTIVITY_TIMEOUT - this.pausedTime);
        }
        return Math.max(0, INACTIVITY_TIMEOUT - (Date.now() - this.lastActivityTime));
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
