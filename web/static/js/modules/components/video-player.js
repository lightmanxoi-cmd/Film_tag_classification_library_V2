/**
 * 视频播放器组件
 */

import { fetchWithAuth } from '../api/fetch.js';

const MIME_TYPES = {
    '.mp4': 'video/mp4',
    '.mkv': 'video/x-matroska',
    '.webm': 'video/webm',
    '.avi': 'video/x-msvideo',
    '.wmv': 'video/x-ms-wmv',
    '.mov': 'video/quicktime'
};

const NON_NATIVE_FORMATS = ['.mkv', '.wmv', '.avi'];

export class VideoPlayer {
    constructor(containerId, videoElementId) {
        this.container = document.getElementById(containerId);
        this.videoElementId = videoElementId;
        this.player = null;
        this.currentVideoPath = '';
    }

    async play(videoId, title, tags, filePath) {
        try {
            this.currentVideoPath = filePath;
            
            const response = await fetchWithAuth(`/api/video/stream/${videoId}`);
            const result = await response.json();
            
            if (result.success) {
                this._setupModal(result.data, title, tags);
                this._initPlayer(result.data);
                return true;
            }
            return false;
        } catch (error) {
            console.error('获取视频信息失败:', error);
            throw error;
        }
    }

    _setupModal(data, title, tags) {
        const modal = this.container;
        const formatNotice = modal.querySelector('#formatNotice');
        
        const titleEl = modal.querySelector('#modalTitle');
        if (titleEl) titleEl.textContent = title;
        
        const tagsContainer = modal.querySelector('#modalTags');
        if (tagsContainer && tags) {
            const childTags = tags.filter(t => t.parent_id);
            tagsContainer.innerHTML = childTags.map(t => 
                `<span class="video-tag">${t.name}</span>`
            ).join('');
        }
        
        if (formatNotice) {
            const fileExt = data.file_ext || '.mp4';
            formatNotice.style.display = NON_NATIVE_FORMATS.includes(fileExt) ? 'block' : 'none';
        }
        
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    _initPlayer(data) {
        this._destroyPlayer();
        
        let videoElement = document.getElementById(this.videoElementId);
        
        if (!videoElement || !document.body.contains(videoElement)) {
            videoElement = document.createElement('video');
            videoElement.id = this.videoElementId;
            videoElement.className = 'video-js vjs-big-play-centered vjs-fluid';
            videoElement.controls = true;
            videoElement.preload = 'auto';
            videoElement.setAttribute('playsinline', '');
            videoElement.setAttribute('webkit-playsinline', '');
            
            const playerActions = this.container.querySelector('.player-actions');
            this.container.querySelector('.modal-content').insertBefore(videoElement, playerActions);
        }
        
        if (typeof videojs !== 'undefined') {
            this.player = videojs(this.videoElementId, {
                fluid: true,
                responsive: true,
                muted: true,
                playbackRates: [0.5, 1, 1.25, 1.5, 2],
                controlBar: {
                    children: [
                        'playToggle',
                        'volumePanel',
                        'currentTimeDisplay',
                        'timeDivider',
                        'durationDisplay',
                        'progressControl',
                        'playbackRateMenuButton',
                        'fullscreenToggle'
                    ]
                }
            });
            
            this.player.src({
                src: data.stream_url,
                type: this._getMimeType(data.file_ext)
            });
            
            this.player.ready(function() {
                this.play().catch(function(error) {
                    console.log('自动播放失败，请手动点击播放:', error);
                });
            });
        } else {
            console.warn('Video.js 不可用，使用原生播放器');
            let videoElement = document.getElementById(this.videoElementId);
            if (!videoElement || videoElement.classList.contains('video-js')) {
                const oldElement = videoElement;
                videoElement = document.createElement('video');
                videoElement.id = this.videoElementId;
                videoElement.controls = true;
                videoElement.preload = 'auto';
                videoElement.style.width = '100%';
                videoElement.setAttribute('playsinline', '');
                
                if (oldElement && oldElement.parentNode) {
                    oldElement.parentNode.replaceChild(videoElement, oldElement);
                } else {
                    const playerActions = this.container.querySelector('.player-actions');
                    this.container.querySelector('.modal-content').insertBefore(videoElement, playerActions);
                }
            }
            
            videoElement.src = data.stream_url;
            videoElement.muted = true;
            videoElement.play().catch(function(error) {
                console.log('自动播放失败，请手动点击播放:', error);
            });
            
            this.player = {
                play: () => videoElement.play(),
                pause: () => videoElement.pause(),
                dispose: () => {
                    videoElement.pause();
                    videoElement.src = '';
                },
                src: (src) => { videoElement.src = src.src; },
                ready: (fn) => { 
                    if (videoElement.readyState >= 1) fn.call({ play: () => videoElement.play() });
                    else videoElement.addEventListener('loadedmetadata', fn);
                },
                on: (event, fn) => videoElement.addEventListener(event, fn),
                paused: () => videoElement.paused
            };
        }
    }

    _getMimeType(ext) {
        return MIME_TYPES[ext] || 'video/mp4';
    }

    _destroyPlayer() {
        if (this.player) {
            try {
                this.player.dispose();
            } catch (e) {
                console.log('Dispose error:', e);
            }
            this.player = null;
        }
    }

    close() {
        this._destroyPlayer();
        this.container.classList.remove('show');
        document.body.style.overflow = '';
    }

    isPlaying() {
        return this.player && !this.player.paused();
    }

    pause() {
        if (this.player) {
            this.player.pause();
        }
    }

    play() {
        if (this.player) {
            this.player.play();
        }
    }
}

export function getMimeType(ext) {
    return MIME_TYPES[ext] || 'video/mp4';
}

export function isNonNativeFormat(ext) {
    return NON_NATIVE_FORMATS.includes(ext);
}
