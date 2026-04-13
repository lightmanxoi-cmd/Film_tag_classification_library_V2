import { getMimeType } from '../components/video-player.js';

const DESKTOP_CONTROL_BAR = [
    'playToggle',
    'volumePanel',
    'currentTimeDisplay',
    'timeDivider',
    'durationDisplay',
    'progressControl',
    'playbackRateMenuButton',
    'fullscreenToggle'
];

const MOBILE_CONTROL_BAR = [
    'playToggle',
    'volumePanel',
    'currentTimeDisplay',
    'timeDivider',
    'durationDisplay',
    'progressControl',
    'fullscreenToggle'
];

const NON_NATIVE_FORMATS = ['.mkv', '.wmv', '.avi'];

class VideoPlayerManager {
    constructor() {
        this._player = null;
        this._initialized = false;
        this._isMobile = false;
    }

    get player() {
        return this._player;
    }

    _detectMobile() {
        return window.innerWidth <= 1023;
    }

    _getOptions() {
        const isMobile = this._detectMobile();
        this._isMobile = isMobile;

        return {
            fluid: true,
            responsive: true,
            muted: true,
            playbackRates: [0.5, 1, 1.25, 1.5, 2],
            controlBar: {
                children: isMobile ? MOBILE_CONTROL_BAR : DESKTOP_CONTROL_BAR
            },
            html5: {
                vhs: { overrideNative: !isMobile },
                nativeVideoTracks: isMobile,
                nativeAudioTracks: isMobile,
                nativeTextTracks: isMobile
            },
            userActions: { hotkeys: true }
        };
    }

    _ensureVideoElement() {
        let videoElement = document.getElementById('videoPlayer');

        if (videoElement && document.body.contains(videoElement)) {
            return videoElement;
        }

        videoElement = document.createElement('video');
        videoElement.id = 'videoPlayer';
        videoElement.className = 'video-js vjs-big-play-centered vjs-fluid';
        videoElement.controls = true;
        videoElement.preload = 'auto';
        videoElement.setAttribute('playsinline', '');
        videoElement.setAttribute('webkit-playsinline', '');
        videoElement.setAttribute('x5-video-player-type', 'h5');
        videoElement.setAttribute('x5-video-player-fullscreen', 'true');

        const playerContainer = document.querySelector('.modal-content');
        const playerActions = document.querySelector('.player-actions');
        playerContainer.insertBefore(videoElement, playerActions);

        return videoElement;
    }

    _initVideoJs(streamUrl, fileExt) {
        this._ensureVideoElement();

        const options = this._getOptions();
        this._player = videojs('videoPlayer', options);

        this._player.src({
            src: streamUrl,
            type: getMimeType(fileExt)
        });

        this._player.ready(function () {
            this.play().catch(function (error) {
                console.log('自动播放失败，请手动点击播放:', error);
            });
        });

        if (this._isMobile) {
            this._setupMobileFullscreen();
        }
    }

    _initNativePlayer(streamUrl) {
        let videoElement = document.getElementById('videoPlayer');

        if (!videoElement || videoElement.classList.contains('video-js')) {
            const oldElement = videoElement;
            videoElement = document.createElement('video');
            videoElement.id = 'videoPlayer';
            videoElement.controls = true;
            videoElement.preload = 'auto';
            videoElement.style.width = '100%';
            videoElement.setAttribute('playsinline', '');

            if (oldElement && oldElement.parentNode) {
                oldElement.parentNode.replaceChild(videoElement, oldElement);
            } else {
                const playerActions = document.querySelector('.player-actions');
                document.querySelector('.modal-content').insertBefore(videoElement, playerActions);
            }
        }

        videoElement.src = streamUrl;
        videoElement.muted = true;
        videoElement.play().catch(function (error) {
            console.log('自动播放失败，请手动点击播放:', error);
        });

        this._player = this._createNativeAdapter(videoElement);
    }

    _createNativeAdapter(el) {
        return {
            play: () => el.play(),
            pause: () => el.pause(),
            dispose: () => {
                el.pause();
                el.src = '';
            },
            src: (src) => { el.src = src.src; },
            ready: (fn) => {
                if (el.readyState >= 1) fn.call({ play: () => el.play() });
                else el.addEventListener('loadedmetadata', fn);
            },
            on: (event, fn) => el.addEventListener(event, fn),
            paused: () => el.paused
        };
    }

    _setupMobileFullscreen() {
        if (!this._player) return;

        const modal = document.getElementById('videoModal');
        this._player.on('fullscreenchange', function () {
            if (this.isFullscreen()) {
                modal.classList.add('is-fullscreen');
                if (screen.orientation && screen.orientation.lock) {
                    screen.orientation.lock('landscape').catch(() => {});
                }
            } else {
                modal.classList.remove('is-fullscreen');
                if (screen.orientation && screen.orientation.unlock) {
                    screen.orientation.unlock();
                }
            }
        });
    }

    _updateModal(data, videoTags) {
        const modal = document.getElementById('videoModal');
        const formatNotice = document.getElementById('formatNotice');

        document.getElementById('modalTitle').textContent = data.title;

        const tagsContainer = document.getElementById('modalTags');
        const childTags = videoTags.filter(t => t.parent_id);
        tagsContainer.innerHTML = childTags.map(t =>
            `<span class="video-tag">${t.name}</span>`
        ).join('');

        const fileExt = data.file_ext || '.mp4';
        formatNotice.style.display = NON_NATIVE_FORMATS.includes(fileExt) ? 'block' : 'none';

        const isMobile = this._detectMobile();
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';

        if (isMobile) {
            modal.classList.add('mobile-mode');
        }
    }

    play(streamUrl, fileExt, videoTags, data) {
        this._updateModal(data, videoTags);

        if (this._player) {
            try {
                this._player.dispose();
            } catch (e) {
                console.log('Dispose error:', e);
            }
            this._player = null;
        }

        if (typeof videojs !== 'undefined') {
            this._initVideoJs(streamUrl, fileExt);
        } else {
            console.warn('Video.js 不可用，使用原生播放器');
            this._initNativePlayer(streamUrl);
        }
    }

    close() {
        if (this._player) {
            this._player.pause();
            try {
                this._player.dispose();
            } catch (e) {
                console.log('Dispose error:', e);
            }
            this._player = null;
        }

        const modal = document.getElementById('videoModal');
        modal.classList.remove('show', 'mobile-mode', 'is-fullscreen');
        document.body.style.overflow = '';

        if (screen.orientation && screen.orientation.unlock) {
            screen.orientation.unlock().catch(() => {});
        }
    }
}

export const videoPlayerManager = new VideoPlayerManager();
