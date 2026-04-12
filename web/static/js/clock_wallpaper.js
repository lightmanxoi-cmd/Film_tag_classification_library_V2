/**
 * 视频时钟壁纸播放器
 * 
 * 本文件实现了一个特殊的视频播放模式，具有以下特点：
 * - 随机播放视频列表中的视频
 * - 支持时钟叠加显示
 * - 支持分段浏览模式（将视频分成10段快速预览）
 * - 支持全屏播放和视频适配模式切换
 * - 自动隐藏控制栏
 * - 时钟尺寸调节和位置拖拽
 * - Electron状态记忆
 * 
 * 主要功能模块：
 * 1. 视频加载模块：loadVideos、initShuffledIndices
 * 2. 播放控制模块：playNextVideo、togglePlay、toggleMute
 * 3. 分段播放模块：startSegmentPlayback、toggleBrowseMode
 * 4. UI控制模块：toggleFullscreen、toggleClock、toggleVideoFitMode
 * 5. 时钟显示模块：startClock
 * 
 * 作者：Video Library System
 * 创建时间：2024
 */

import { ClockController, injectClockStyles } from './modules/components/clock-controller.js';

/* ==================== 全局变量定义 ==================== */

/** 时钟控制器实例 */
let clockController = null;

/** 视频列表数据 */
let videos = [];

/** 筛选参数（用于重新加载视频） */
let filterParams = null;

/** 当前播放索引 */
let currentPlayIndex = 0;

/** 当前播放的视频在原数组中的索引 */
let currentVideoIndex = -1;

/** 是否正在播放 */
let isPlaying = false;

/** 当前播放时间 */
let currentTime = 0;

/** 视频总时长 */
let duration = 0;

/** 当前音量值 */
let volume = 0;

/** 是否静音 */
let isMuted = true;

/** 是否显示控制栏 */
let showControls = true;

/** 是否已经开始播放过 */
let hasStarted = false;

/** 是否正在切换视频 */
let isSwitchingVideo = false;

/** 是否处于全屏模式 */
let isFullscreen = false;

/** 是否启用分段浏览模式 */
let browseMode = false;

/** 当前播放的分段索引（0-9） */
let currentSegment = 0;

/** 是否显示时钟 */
let showClock = true;

/** 视频适配模式：cover（填充）或 contain（适应） */
let videoFitMode = 'cover';

/** 控制栏自动隐藏的定时器 */
let controlsTimeout = null;

/** 分段播放的定时器 */
let segmentTimeout = null;

/** 上次点击时间（用于双击检测） */
let lastClickTime = 0;

/* ==================== DOM 元素引用 ==================== */

/** 视频播放器元素 */
const video = document.getElementById('videoPlayer');

/** 加载屏幕元素 */
const loadingScreen = document.getElementById('loadingScreen');

/** 播放器容器元素 */
const playerContainer = document.getElementById('playerContainer');

/** 时钟叠加层元素 */
const clockOverlay = document.getElementById('clockOverlay');

/** 时钟时间显示元素 */
const clockTime = document.getElementById('clockTime');

/** 顶部栏元素 */
const topBar = document.getElementById('topBar');

/** 控制栏叠加层元素 */
const controlsOverlay = document.getElementById('controlsOverlay');

/** 视频名称显示元素 */
const videoName = document.getElementById('videoName');

/** 视频数量显示元素 */
const videoCount = document.getElementById('videoCount');

/** 进度条元素 */
const progressBar = document.getElementById('progressBar');

/** 当前时间显示元素 */
const currentTimeEl = document.getElementById('currentTime');

/** 总时长显示元素 */
const durationEl = document.getElementById('duration');

/** 播放/暂停按钮 */
const playBtn = document.getElementById('playBtn');

/** 跳过按钮 */
const skipBtn = document.getElementById('skipBtn');

/** 音量按钮 */
const volumeBtn = document.getElementById('volumeBtn');

/** 音量滑块 */
const volumeSlider = document.getElementById('volumeSlider');

/** 全屏按钮 */
const fullscreenBtn = document.getElementById('fullscreenBtn');

/** 时钟切换按钮 */
const clockToggleBtn = document.getElementById('clockToggleBtn');

/** 视频适配模式按钮 */
const fitModeBtn = document.getElementById('fitModeBtn');

/** 分段浏览模式按钮 */
const browseModeBtn = document.getElementById('browseModeBtn');

/** 分段指示器元素 */
const segmentIndicator = document.getElementById('segmentIndicator');

/* ==================== 核心功能函数 ==================== */

/**
 * 带认证的 fetch 封装
 * 
 * 封装原生 fetch，自动处理 401 未授权响应。
 * 当用户未登录时，跳转到登录页面。
 * 
 * @param {string} url - 请求URL
 * @param {Object} options - fetch 选项
 * @returns {Promise<Response>} fetch 响应
 * @throws {Error} 当响应状态为 401 时抛出错误
 */
async function fetchWithAuth(url, options = {}) {
    const response = await fetch(url, options);
    if (response.status === 401) {
        window.location.href = '/login';
        throw new Error('Unauthorized');
    }
    return response;
}

/**
 * 获取URL参数
 * 
 * 从当前页面URL中解析filter参数，用于获取标签筛选条件。
 * 
 * @returns {Object|null} 解析后的筛选条件对象，如果不存在则返回null
 */
function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const filter = params.get('filter');
    if (filter) {
        try {
            return JSON.parse(decodeURIComponent(filter));
        } catch (e) {
            console.error('Failed to parse filter params:', e);
            return null;
        }
    }
    return null;
}

/**
 * 加载视频列表
 * 
 * 根据URL参数中的标签筛选条件，从服务器获取随机排序的视频列表。
 * 服务器返回的列表已经是随机顺序，直接按顺序播放即可。
 */
async function loadVideos() {
    filterParams = getUrlParams();
    
    if (!filterParams) {
        alert('未找到筛选参数');
        window.location.href = '/';
        return;
    }
    
    await loadVideosFromServer();
}

/**
 * 从服务器加载视频列表
 * 
 * @param {boolean} autoPlay - 是否自动开始播放
 */
async function loadVideosFromServer(autoPlay = true) {
    try {
        const response = await fetchWithAuth('/api/v1/random-queue/rx/videos', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tags_by_category: filterParams
            })
        });
        
        const result = await response.json();
        
        if (result.success && result.data.videos.length > 0) {
            videos = result.data.videos;
            videoCount.textContent = `${videos.length} 个视频`;
            currentPlayIndex = 0;
            
            if (loadingScreen.style.display !== 'none') {
                loadingScreen.style.display = 'none';
                playerContainer.style.display = 'block';
                startClock();
                setupEventListeners();
                initClockController();
            }
            
            if (autoPlay) {
                playNextVideo();
            }
        } else {
            loadingScreen.innerHTML = `
                <p>未找到视频</p>
                <button onclick="goBack()" style="margin-top: 1rem; padding: 0.5rem 1rem; cursor: pointer;">返回</button>
            `;
        }
    } catch (error) {
        console.error('Failed to load videos:', error);
        loadingScreen.innerHTML = `
            <p>加载视频失败</p>
            <button onclick="goBack()" style="margin-top: 1rem; padding: 0.5rem 1rem; cursor: pointer;">返回</button>
        `;
    }
}

/**
 * 播放下一个视频
 * 
 * 按顺序播放视频列表中的下一个。
 * 如果所有视频都已播放，则重新从服务器获取新的随机列表。
 */
function playNextVideo() {
    if (videos.length === 0) return;
    
    if (currentPlayIndex >= videos.length) {
        console.log('[ClockWallpaper] 播放列表完成，循环播放');
        currentPlayIndex = 0;
    }
    
    isSwitchingVideo = true;
    showControls = false;
    updateControlsVisibility();
    
    if (segmentTimeout) {
        clearTimeout(segmentTimeout);
        segmentTimeout = null;
    }
    
    currentSegment = 1;
    
    const videoData = videos[currentPlayIndex];
    currentVideoIndex = currentPlayIndex;
    currentPlayIndex++;
    
    video.src = `/video/stream/${videoData.id}`;
    videoName.textContent = videoData.title;
    
    updateVideoTagsDisplay(videoData);
    
    currentTime = 0;
    hasStarted = false;
    isPlaying = true;
    
    video.load();
    
    const playOnLoad = () => {
        video.play().catch(e => {
            console.log('Auto-play prevented, will retry on user interaction:', e);
        });
        video.removeEventListener('canplaythrough', playOnLoad);
        video.removeEventListener('loadeddata', playOnLoad);
    };
    
    video.addEventListener('canplaythrough', playOnLoad);
    video.addEventListener('loadeddata', playOnLoad);
}

/* ==================== 分段播放功能 ==================== */

/**
 * 启动分段播放模式
 * 
 * 将视频分成10个等分段，每段播放30秒，总共浓缩为5分钟浏览。
 * 用于快速浏览长视频内容。
 * 
 * @param {number} videoDuration - 视频总时长（秒）
 */
function startSegmentPlayback(videoDuration) {
    console.log('[BrowseMode] Starting segment playback, duration:', videoDuration);
    
    const segmentDuration = videoDuration / 10;
    const segmentPlayTime = 30;
    let currentSeg = 0;
    
    const playNextSegment = () => {
        if (currentSeg >= 10) {
            console.log('[BrowseMode] All segments played, playing next video');
            playNextVideo();
            return;
        }
        
        const segmentStartTime = currentSeg * segmentDuration;
        console.log('[BrowseMode] Jumping to segment', currentSeg + 1, 'at time:', segmentStartTime);
        
        video.currentTime = segmentStartTime;
        currentTime = segmentStartTime;
        progressBar.value = currentTime;
        currentTimeEl.textContent = formatTime(currentTime);
        
        if (video.paused) {
            video.play().catch(() => {});
        }
        
        segmentTimeout = setTimeout(() => {
            currentSeg++;
            currentSegment = currentSeg;
            segmentIndicator.textContent = `${currentSeg}/10`;
            playNextSegment();
        }, segmentPlayTime * 1000);
    };
    
    currentSegment = 1;
    segmentIndicator.textContent = '1/10';
    playNextSegment();
}

/* ==================== 事件监听器设置 ==================== */

/**
 * 设置所有事件监听器
 * 
 * 为视频播放器和控制按钮绑定各种事件处理函数。
 */
function setupEventListeners() {
    video.addEventListener('loadedmetadata', () => {
        duration = video.duration;
        progressBar.max = duration;
        durationEl.textContent = formatTime(duration);
        
        console.log('[BrowseMode] loadedmetadata, browseMode:', browseMode, 'duration:', video.duration);
        
        if (browseMode && video.duration > 300) {
            if (segmentTimeout) {
                clearTimeout(segmentTimeout);
                segmentTimeout = null;
            }
            console.log('[BrowseMode] Starting segment playback from loadedmetadata');
            setTimeout(() => {
                startSegmentPlayback(video.duration);
            }, 100);
        }
    });
    
    video.addEventListener('timeupdate', () => {
        currentTime = video.currentTime;
        progressBar.value = currentTime;
        currentTimeEl.textContent = formatTime(currentTime);
    });
    
    video.addEventListener('play', () => {
        isPlaying = true;
        hasStarted = true;
        updatePlayButton();
        isSwitchingVideo = false;
    });
    
    video.addEventListener('pause', () => {
        isPlaying = false;
        updatePlayButton();
    });
    
    video.addEventListener('ended', () => {
        if (segmentTimeout) {
            clearTimeout(segmentTimeout);
        }
        
        if (browseMode) {
            if (video.duration <= 300) {
                playNextVideo();
            }
            return;
        }
        
        playNextVideo();
    });
    
    video.addEventListener('error', (e) => {
        console.error('Video error:', e);
        if (segmentTimeout) {
            clearTimeout(segmentTimeout);
        }
        setTimeout(() => {
            playNextVideo();
        }, 1000);
    });
    
    video.addEventListener('click', handleVideoClick);
    
    playBtn.addEventListener('click', togglePlay);
    skipBtn.addEventListener('click', playNextVideo);
    volumeBtn.addEventListener('click', toggleMute);
    volumeSlider.addEventListener('input', handleVolumeChange);
    fullscreenBtn.addEventListener('click', toggleFullscreen);
    clockToggleBtn.addEventListener('click', toggleClock);
    fitModeBtn.addEventListener('click', toggleVideoFitMode);
    browseModeBtn.addEventListener('click', toggleBrowseMode);
    progressBar.addEventListener('input', handleSeek);
    
    playerContainer.addEventListener('mousemove', handleMouseMove);
    playerContainer.addEventListener('click', handleMouseMove);
    
    playerContainer.addEventListener('touchstart', handleTouchStart, { passive: true });
    playerContainer.addEventListener('touchend', handleTouchEnd, { passive: true });
    
    document.addEventListener('keydown', handleKeydown);
    document.addEventListener('fullscreenchange', handleFullscreenChange);
}

let touchStartX = 0;
let touchStartY = 0;
let touchStartTime = 0;

function handleTouchStart(e) {
    if (e.touches.length === 1) {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        touchStartTime = Date.now();
    }
}

function handleTouchEnd(e) {
    if (e.changedTouches.length !== 1) return;
    
    const touchEndX = e.changedTouches[0].clientX;
    const touchEndY = e.changedTouches[0].clientY;
    const touchDuration = Date.now() - touchStartTime;
    
    const diffX = touchEndX - touchStartX;
    const diffY = touchEndY - touchStartY;
    
    if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50 && touchDuration < 500) {
        if (diffX < 0) {
            playNextVideo();
        }
    }
}

/* ==================== 播放控制函数 ==================== */

/**
 * 处理视频点击事件
 * 
 * 实现单击暂停/播放，双击切换全屏或退出。
 * 在全屏模式下双击会退出并返回上一页。
 */
function handleVideoClick() {
    const now = Date.now();
    const timeSinceLastClick = now - lastClickTime;
    lastClickTime = now;
    
    if (timeSinceLastClick < 300) {
        if (isFullscreen) {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            }
            goBack();
            return;
        } else {
            toggleFullscreen();
            return;
        }
    }
    
    togglePlay();
}

/**
 * 切换播放/暂停状态
 */
function togglePlay() {
    if (video.paused) {
        video.play();
    } else {
        video.pause();
    }
}

/**
 * 更新播放按钮图标
 * 
 * 根据当前播放状态更新按钮显示的图标（播放或暂停）。
 */
function updatePlayButton() {
    if (isPlaying) {
        playBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
            </svg>
        `;
    } else {
        playBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M8 5v14l11-7z" />
            </svg>
        `;
    }
}

/* ==================== 音量控制函数 ==================== */

/**
 * 处理音量滑块变化
 * 
 * @param {Event} e - input 事件对象
 */
function handleVolumeChange(e) {
    volume = parseFloat(e.target.value);
    video.volume = volume;
    if (volume > 0) {
        isMuted = false;
        video.muted = false;
    }
    updateVolumeButton();
}

/**
 * 切换静音状态
 */
function toggleMute() {
    isMuted = !isMuted;
    video.muted = isMuted;
    if (!isMuted && volume === 0) {
        volume = 0.5;
        video.volume = 0.5;
        volumeSlider.value = 0.5;
    }
    updateVolumeButton();
}

/**
 * 更新音量按钮图标
 * 
 * 根据当前音量和静音状态显示不同的图标。
 */
function updateVolumeButton() {
    if (isMuted || volume === 0) {
        volumeBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z" />
            </svg>
        `;
    } else if (volume < 0.5) {
        volumeBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM5 9v6h4l5 5V4L9 9H5z" />
            </svg>
        `;
    } else {
        volumeBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
            </svg>
        `;
    }
}

/* ==================== 进度控制函数 ==================== */

/**
 * 处理进度条拖动
 * 
 * @param {Event} e - input 事件对象
 */
function handleSeek(e) {
    const newTime = parseFloat(e.target.value);
    video.currentTime = newTime;
    currentTime = newTime;
}

/* ==================== 全屏控制函数 ==================== */

/**
 * 切换全屏模式
 */
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        playerContainer.requestFullscreen();
        isFullscreen = true;
    } else {
        document.exitFullscreen();
        isFullscreen = false;
    }
    updateFullscreenButton();
}

/**
 * 处理全屏状态变化事件
 */
function handleFullscreenChange() {
    isFullscreen = !!document.fullscreenElement;
    updateFullscreenButton();
}

/**
 * 更新全屏按钮图标
 */
function updateFullscreenButton() {
    if (isFullscreen) {
        fullscreenBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z" />
            </svg>
        `;
    } else {
        fullscreenBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" />
            </svg>
        `;
    }
}

/* ==================== 特殊功能切换函数 ==================== */

/**
 * 切换时钟显示
 */
function toggleClock() {
    if (clockController) {
        const visible = clockController.toggle();
        clockToggleBtn.classList.toggle('active', visible);
    } else {
        showClock = !showClock;
        clockOverlay.classList.toggle('hidden', !showClock);
        clockToggleBtn.classList.toggle('active', showClock);
    }
}

/**
 * 切换视频适配模式
 * 
 * 在 cover（填充裁剪）和 contain（完整显示）模式之间切换。
 */
function toggleVideoFitMode() {
    videoFitMode = videoFitMode === 'cover' ? 'contain' : 'cover';
    video.className = `video-player video-fit-${videoFitMode}`;
    fitModeBtn.querySelector('span').textContent = videoFitMode === 'cover' ? '覆盖' : '适应';
}

/**
 * 切换分段浏览模式
 * 
 * 开启后将超过5分钟的视频分成10段快速预览，每段播放视频总时长的十分之一。
 * 关闭后恢复正常播放模式。
 */
function toggleBrowseMode() {
    browseMode = !browseMode;
    browseModeBtn.classList.toggle('active', browseMode);
    
    console.log('[BrowseMode] Toggle browse mode:', browseMode, 'video duration:', video.duration);
    
    if (browseMode) {
        segmentIndicator.style.display = 'inline';
    } else {
        segmentIndicator.style.display = 'none';
    }
    
    currentSegment = 1;
    
    if (segmentTimeout) {
        clearTimeout(segmentTimeout);
        segmentTimeout = null;
    }
    
    if (browseMode && video.duration && video.duration > 300) {
        console.log('[BrowseMode] Starting segment playback from toggle');
        video.currentTime = 0;
        currentTime = 0;
        progressBar.value = 0;
        currentTimeEl.textContent = formatTime(0);
        if (video.paused) {
            video.play().catch(() => {});
        }
        startSegmentPlayback(video.duration);
    } else if (!browseMode) {
        currentTime = video.currentTime;
    }
}

/* ==================== 控制栏显示控制 ==================== */

/**
 * 处理鼠标移动事件
 * 
 * 显示控制栏并重置自动隐藏定时器。
 * 在全屏模式下还会临时显示鼠标光标。
 */
function handleMouseMove() {
    if (isSwitchingVideo) {
        isSwitchingVideo = false;
    }
    showControls = true;
    updateControlsVisibility();
    resetControlsTimeout();
    
    if (isFullscreen && playerContainer) {
        playerContainer.classList.add('show-cursor');
        if (playerContainer.dataset.cursorTimeout) {
            clearTimeout(parseInt(playerContainer.dataset.cursorTimeout));
        }
        const timeoutId = setTimeout(() => {
            playerContainer.classList.remove('show-cursor');
        }, 1000);
        playerContainer.dataset.cursorTimeout = timeoutId.toString();
    }
}

/**
 * 重置控制栏自动隐藏定时器
 * 
 * 设置1秒后自动隐藏控制栏（如果正在播放且不在切换视频）。
 */
function resetControlsTimeout() {
    if (controlsTimeout) {
        clearTimeout(controlsTimeout);
    }
    if (isSwitchingVideo) {
        showControls = false;
        updateControlsVisibility();
        return;
    }
    showControls = true;
    updateControlsVisibility();
    controlsTimeout = setTimeout(() => {
        if (isPlaying && hasStarted && !isSwitchingVideo) {
            showControls = false;
            updateControlsVisibility();
        }
    }, 1000);
}

/**
 * 更新控制栏可见性
 */
function updateControlsVisibility() {
    topBar.classList.toggle('hidden', !showControls);
    controlsOverlay.classList.toggle('hidden', !showControls);
}

function updateVideoTagsDisplay(videoData) {
    const tagsDisplay = document.getElementById('videoTagsDisplay');
    if (!tagsDisplay) return;
    
    if (!videoData.tags || videoData.tags.length === 0) {
        tagsDisplay.innerHTML = '';
        return;
    }
    
    const level2Tags = videoData.tags.filter(t => t.parent_id !== null && t.parent_id !== undefined);
    
    if (level2Tags.length === 0) {
        tagsDisplay.innerHTML = '';
        return;
    }
    
    tagsDisplay.innerHTML = level2Tags.map(t => 
        `<span class="tag-chip">${t.name}</span>`
    ).join('');
}

/* ==================== 键盘事件处理 ==================== */

/**
 * 处理键盘按键事件
 * 
 * 支持的快捷键：
 * - Escape: 退出全屏或返回上一页
 * - Space: 暂停/播放
 * - ArrowRight: 快进10秒
 * - ArrowLeft: 后退10秒
 * 
 * @param {KeyboardEvent} e - 键盘事件对象
 */
function handleKeydown(e) {
    if (e.key === 'Escape') {
        if (isFullscreen) {
            document.exitFullscreen();
        } else {
            goBack();
        }
    } else if (e.key === ' ') {
        e.preventDefault();
        togglePlay();
    } else if (e.key === 'ArrowRight') {
        video.currentTime += 10;
    } else if (e.key === 'ArrowLeft') {
        video.currentTime -= 10;
    }
}

/* ==================== 工具函数 ==================== */

/**
 * 格式化时间显示
 * 
 * 将秒数转换为 分:秒 格式。
 * 
 * @param {number} time - 时间（秒）
 * @returns {string} 格式化后的时间字符串
 */
function formatTime(time) {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * 启动时钟显示
 * 
 * 每秒更新一次时钟显示，使用12小时制格式。
 */
function startClock() {
    const updateClock = () => {
        const now = new Date();
        let hours = now.getHours();
        const minutes = now.getMinutes();
        const seconds = now.getSeconds();
        hours = hours % 12;
        hours = hours ? hours : 12;
        const minutesStr = minutes.toString().padStart(2, '0');
        const secondsStr = seconds.toString().padStart(2, '0');
        clockTime.textContent = `${hours}:${minutesStr}:${secondsStr}`;
    };
    
    updateClock();
    setInterval(updateClock, 1000);
}

/* ==================== 会话保活 ==================== */

/**
 * 会话保活定时器
 * 每分钟向服务器发送请求，保持session活跃
 */
let sessionKeepAliveInterval = null;

function startSessionKeepAlive() {
    if (sessionKeepAliveInterval) return;
    
    sessionKeepAliveInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/v1/stats', {
                credentials: 'include'
            });
            if (response.status === 401) {
                console.log('[Session] 会话已过期，停止保活');
                stopSessionKeepAlive();
            }
        } catch (e) {
            console.log('[Session] 保活请求失败:', e.message);
        }
    }, 60000);
    
    console.log('[Session] 会话保活已启动');
}

function stopSessionKeepAlive() {
    if (sessionKeepAliveInterval) {
        clearInterval(sessionKeepAliveInterval);
        sessionKeepAliveInterval = null;
        console.log('[Session] 会话保活已停止');
    }
}

/**
 * 返回上一页
 * 
 * 清理定时器并跳转到首页。
 */
function goBack() {
    if (segmentTimeout) {
        clearTimeout(segmentTimeout);
    }
    if (controlsTimeout) {
        clearTimeout(controlsTimeout);
    }
    stopSessionKeepAlive();
    window.location.href = '/';
}

window.goBack = goBack;

/* ==================== 初始化 ==================== */

/**
 * 页面加载完成后初始化
 */
document.addEventListener('DOMContentLoaded', () => {
    injectClockStyles();
    
    loadVideos();
    startSessionKeepAlive();
});

export function initClockController() {
    if (clockController) {
        console.log('[ClockWallpaper] ClockController already initialized');
        return;
    }
    
    console.log('[ClockWallpaper] Initializing ClockController');
    console.log('[ClockWallpaper] clockOverlay:', clockOverlay);
    console.log('[ClockWallpaper] playerContainer:', playerContainer);
    
    clockController = new ClockController({
        clockElement: clockOverlay,
        containerElement: playerContainer,
        pageId: 'clock_wallpaper'
    });
    
    console.log('[ClockWallpaper] ClockController created:', clockController);
}

window.initClockController = initClockController;
