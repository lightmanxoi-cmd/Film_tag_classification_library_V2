import { appState } from '../stores/state.js';
import { videoService } from '../services/video.js';
import { showToast } from '../components/toast.js';
import { getMimeType } from '../components/video-player.js';

let videoPlayer = null;

function getVideoPlayer() {
    return videoPlayer;
}

function setVideoPlayer(player) {
    videoPlayer = player;
}

export async function playVideo(videoIdOrVideo, title, tags) {
    try {
        let videoId, videoTitle, videoTags;

        if (typeof videoIdOrVideo === 'object' && videoIdOrVideo !== null) {
            videoId = videoIdOrVideo.id;
            videoTitle = videoIdOrVideo.title;
            videoTags = videoIdOrVideo.tags;
        } else {
            videoId = videoIdOrVideo;
            videoTitle = title;
            videoTags = tags;
        }

        const data = await videoService.getVideoStreamUrl(videoId);

        const modal = document.getElementById('videoModal');
        const formatNotice = document.getElementById('formatNotice');

        document.getElementById('modalTitle').textContent = data.title;

        const tagsContainer = document.getElementById('modalTags');
        const childTags = videoTags.filter(t => t.parent_id);
        tagsContainer.innerHTML = childTags.map(t =>
            `<span class="video-tag">${t.name}</span>`
        ).join('');

        const fileExt = data.file_ext || '.mp4';
        const nonNativeFormats = ['.mkv', '.wmv', '.avi'];

        if (nonNativeFormats.includes(fileExt)) {
            formatNotice.style.display = 'block';
        } else {
            formatNotice.style.display = 'none';
        }

        const playerContainer = document.querySelector('.modal-content');
        let videoElement = document.getElementById('videoPlayer');

        if (getVideoPlayer()) {
            try {
                getVideoPlayer().dispose();
            } catch (e) {
                console.log('Dispose error:', e);
            }
            setVideoPlayer(null);
        }

        if (!videoElement || !document.body.contains(videoElement)) {
            videoElement = document.createElement('video');
            videoElement.id = 'videoPlayer';
            videoElement.className = 'video-js vjs-big-play-centered vjs-fluid';
            videoElement.controls = true;
            videoElement.preload = 'auto';
            videoElement.setAttribute('playsinline', '');
            videoElement.setAttribute('webkit-playsinline', '');
            videoElement.setAttribute('x5-video-player-type', 'h5');
            videoElement.setAttribute('x5-video-player-fullscreen', 'true');

            const playerActions = document.querySelector('.player-actions');
            playerContainer.insertBefore(videoElement, playerActions);
        }

        const isMobile = window.innerWidth <= 1023;

        const playerOptions = {
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
            },
            html5: {
                vhs: { overrideNative: !isMobile },
                nativeVideoTracks: isMobile,
                nativeAudioTracks: isMobile,
                nativeTextTracks: isMobile
            },
            userActions: { hotkeys: true }
        };

        if (isMobile) {
            playerOptions.controlBar = {
                children: [
                    'playToggle',
                    'volumePanel',
                    'currentTimeDisplay',
                    'timeDivider',
                    'durationDisplay',
                    'progressControl',
                    'fullscreenToggle'
                ]
            };
        }

        modal.classList.add('show');
        document.body.style.overflow = 'hidden';

        if (isMobile) {
            modal.classList.add('mobile-mode');
        }

        if (typeof videojs !== 'undefined') {
            const player = videojs('videoPlayer', playerOptions);
            setVideoPlayer(player);

            getVideoPlayer().src({
                src: data.stream_url,
                type: getMimeType(fileExt)
            });

            getVideoPlayer().ready(function () {
                this.play().catch(function (error) {
                    console.log('自动播放失败，请手动点击播放:', error);
                });

                if (isMobile) {
                    this.on('fullscreenchange', function () {
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
            });
        } else {
            console.warn('Video.js 不可用，使用原生播放器');
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

            videoElement.src = data.stream_url;
            videoElement.muted = true;
            videoElement.play().catch(function (error) {
                console.log('自动播放失败，请手动点击播放:', error);
            });

            setVideoPlayer({
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
            });
        }
    } catch (error) {
        console.error('获取视频信息失败:', error);
        showToast('无法播放视频: ' + error.message, 'error');
    }
}

export function closeVideoModal() {
    const modal = document.getElementById('videoModal');

    if (getVideoPlayer()) {
        getVideoPlayer().pause();
        getVideoPlayer().dispose();
        setVideoPlayer(null);
    }

    modal.classList.remove('show', 'mobile-mode', 'is-fullscreen');
    document.body.style.overflow = '';

    if (screen.orientation && screen.orientation.unlock) {
        screen.orientation.unlock().catch(() => {});
    }
}
