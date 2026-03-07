/**
 * 随机推荐视频播放器
 * 
 * 本文件实现了一个随机推荐视频播放器，具有以下特点：
 * - 随机播放视频列表中的视频
 * - 支持快进/快退功能（15秒）
 * - 支持全屏播放和视频适配模式切换
 * - 自动隐藏控制栏
 * - 支持触摸手势控制进度条
 * - 支持键盘快捷键
 * 
 * 主要功能模块：
 * 1. 视频加载模块：loadVideos、initShuffledIndices
 * 2. 播放控制模块：playRandomVideo、togglePlay、rewindVideo、forwardVideo
 * 3. 音量控制模块：toggleMute、handleVolumeChange
 * 4. 进度控制模块：handleSeek、handleProgressTouch*
 * 5. UI控制模块：toggleFullscreen、toggleVideoFitMode
 * 
 * 作者：Video Library System
 * 创建时间：2024
 */

/* ==================== 全局变量定义 ==================== */

/** 视频列表数据 */
let videos = [];

/** 随机打乱后的视频索引数组 */
let shuffledIndices = [];

/** 当前随机播放的索引位置 */
let currentShuffleIndex = 0;

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

/** 视频适配模式：cover（填充）或 contain（适应） */
let videoFitMode = 'cover';

/** 控制栏自动隐藏的定时器 */
let controlsTimeout = null;

/** 上次点击时间（用于双击检测） */
let lastClickTime = 0;

/* ==================== DOM 元素引用 ==================== */

/** 视频播放器元素 */
const video = document.getElementById('videoPlayer');

/** 加载屏幕元素 */
const loadingScreen = document.getElementById('loadingScreen');

/** 播放器容器元素 */
const playerContainer = document.getElementById('playerContainer');

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

/** 快退按钮 */
const rewindBtn = document.getElementById('rewindBtn');

/** 快进按钮 */
const forwardBtn = document.getElementById('forwardBtn');

/** 跳过按钮 */
const skipBtn = document.getElementById('skipBtn');

/** 音量按钮 */
const volumeBtn = document.getElementById('volumeBtn');

/** 音量滑块 */
const volumeSlider = document.getElementById('volumeSlider');

/** 全屏按钮 */
const fullscreenBtn = document.getElementById('fullscreenBtn');

/** 视频适配模式按钮 */
const fitModeBtn = document.getElementById('fitModeBtn');

/* ==================== 核心功能函数 ==================== */

/**
 * 带认证的 fetch 封装
 * 
 * 封装原生 fetch，自动处理 401 未授权响应。
 * 当用户登录过期时，显示提示并跳转到登录页面。
 * 
 * @param {string} url - 请求URL
 * @param {Object} options - fetch 选项
 * @returns {Promise<Response>} fetch 响应
 * @throws {Error} 当响应状态为 401 时抛出错误
 */
async function fetchWithAuth(url, options = {}) {
    const response = await fetch(url, options);
    if (response.status === 401) {
        const data = await response.clone().json().catch(() => ({}));
        if (data.timeout) {
            alert('Session expired, please login again');
        }
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
 * 根据URL参数中的标签筛选条件，从服务器获取视频列表。
 * 加载成功后初始化随机播放索引并开始播放第一个视频。
 */
async function loadVideos() {
    const tagsByCategory = getUrlParams();
    
    if (!tagsByCategory) {
        alert('No filter parameters found');
        window.location.href = '/';
        return;
    }
    
    try {
        const response = await fetchWithAuth('/api/videos/by-tags-advanced', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tags_by_category: tagsByCategory,
                page: 1,
                page_size: 1000
            })
        });
        
        const result = await response.json();
        
        if (result.success && result.data.videos.length > 0) {
            videos = result.data.videos;
            videoCount.textContent = `${videos.length} videos`;
            
            initShuffledIndices();
            
            loadingScreen.style.display = 'none';
            playerContainer.style.display = 'block';
            
            playRandomVideo();
            setupEventListeners();
        } else {
            loadingScreen.innerHTML = `
                <p>No videos found</p>
                <button onclick="goBack()" style="margin-top: 1rem; padding: 0.5rem 1rem; cursor: pointer;">Back</button>
            `;
        }
    } catch (error) {
        console.error('Failed to load videos:', error);
        loadingScreen.innerHTML = `
            <p>Failed to load videos</p>
            <button onclick="goBack()" style="margin-top: 1rem; padding: 0.5rem 1rem; cursor: pointer;">Back</button>
        `;
    }
}

/**
 * 初始化随机播放索引
 * 
 * 创建视频索引数组并使用 Fisher-Yates 算法进行随机打乱，
 * 确保每个视频只播放一次后再重新打乱。
 */
function initShuffledIndices() {
    shuffledIndices = [];
    for (let i = 0; i < videos.length; i++) {
        shuffledIndices.push(i);
    }
    for (let i = shuffledIndices.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffledIndices[i], shuffledIndices[j]] = [shuffledIndices[j], shuffledIndices[i]];
    }
    currentShuffleIndex = 0;
}

/**
 * 播放随机视频
 * 
 * 从随机打乱的索引数组中获取下一个视频并开始播放。
 * 如果所有视频都已播放，则重新打乱索引数组。
 */
function playRandomVideo() {
    if (videos.length === 0) return;
    
    isSwitchingVideo = true;
    showControls = false;
    updateControlsVisibility();
    
    if (currentShuffleIndex >= shuffledIndices.length) {
        initShuffledIndices();
    }
    
    const randomIndex = shuffledIndices[currentShuffleIndex];
    currentShuffleIndex++;
    currentVideoIndex = randomIndex;
    
    const videoData = videos[randomIndex];
    video.src = `/video/stream/${videoData.id}`;
    videoName.textContent = videoData.title;
    
    currentTime = 0;
    hasStarted = false;
    isPlaying = true;
    
    video.load();
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
        playRandomVideo();
    });
    
    video.addEventListener('click', handleVideoClick);
    
    playBtn.addEventListener('click', togglePlay);
    rewindBtn.addEventListener('click', rewindVideo);
    forwardBtn.addEventListener('click', forwardVideo);
    skipBtn.addEventListener('click', playRandomVideo);
    volumeBtn.addEventListener('click', toggleMute);
    volumeSlider.addEventListener('input', handleVolumeChange);
    fullscreenBtn.addEventListener('click', toggleFullscreen);
    fitModeBtn.addEventListener('click', toggleVideoFitMode);
    progressBar.addEventListener('input', handleSeek);
    
    progressBar.addEventListener('touchstart', handleProgressTouchStart, { passive: false });
    progressBar.addEventListener('touchmove', handleProgressTouchMove, { passive: false });
    progressBar.addEventListener('touchend', handleProgressTouchEnd, { passive: false });
    
    playerContainer.addEventListener('mousemove', handleMouseMove);
    playerContainer.addEventListener('click', handleMouseMove);
    
    document.addEventListener('keydown', handleKeydown);
    document.addEventListener('fullscreenchange', handleFullscreenChange);
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
 * 快退视频
 * 
 * 将视频回退15秒，并显示快退指示器。
 */
function rewindVideo() {
    const newTime = Math.max(0, video.currentTime - 15);
    video.currentTime = newTime;
    currentTime = newTime;
    showSkipIndicator(-15);
}

/**
 * 快进视频
 * 
 * 将视频前进15秒，并显示快进指示器。
 */
function forwardVideo() {
    const newTime = Math.min(video.duration || 0, video.currentTime + 15);
    video.currentTime = newTime;
    currentTime = newTime;
    showSkipIndicator(15);
}

/**
 * 显示跳转指示器
 * 
 * 在屏幕上显示快进/快退的秒数提示。
 * 
 * @param {number} seconds - 跳转的秒数（正数为快进，负数为快退）
 */
function showSkipIndicator(seconds) {
    const indicator = document.getElementById('skipIndicator');
    if (indicator) {
        indicator.textContent = seconds > 0 ? `+${seconds}s` : `${seconds}s`;
        indicator.classList.add('visible');
        setTimeout(() => {
            indicator.classList.remove('visible');
        }, 500);
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

/**
 * 处理进度条触摸开始事件
 * 
 * 在移动设备上支持触摸拖动进度条。
 * 
 * @param {TouchEvent} e - 触摸事件对象
 */
function handleProgressTouchStart(e) {
    e.preventDefault();
    const touch = e.touches[0];
    const rect = progressBar.getBoundingClientRect();
    const percent = Math.max(0, Math.min(1, (touch.clientX - rect.left) / rect.width));
    const newTime = percent * duration;
    progressBar.value = newTime;
    video.currentTime = newTime;
    currentTime = newTime;
}

/**
 * 处理进度条触摸移动事件
 * 
 * 在移动设备上支持触摸拖动进度条。
 * 
 * @param {TouchEvent} e - 触摸事件对象
 */
function handleProgressTouchMove(e) {
    e.preventDefault();
    const touch = e.touches[0];
    const rect = progressBar.getBoundingClientRect();
    const percent = Math.max(0, Math.min(1, (touch.clientX - rect.left) / rect.width));
    const newTime = percent * duration;
    progressBar.value = newTime;
    video.currentTime = newTime;
    currentTime = newTime;
    currentTimeEl.textContent = formatTime(newTime);
}

/**
 * 处理进度条触摸结束事件
 * 
 * @param {TouchEvent} e - 触摸事件对象
 */
function handleProgressTouchEnd(e) {
    e.preventDefault();
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

/* ==================== 视频适配模式控制 ==================== */

/**
 * 切换视频适配模式
 * 
 * 在 cover（填充裁剪）和 contain（完整显示）模式之间切换。
 */
function toggleVideoFitMode() {
    videoFitMode = videoFitMode === 'cover' ? 'contain' : 'cover';
    video.className = `video-player video-fit-${videoFitMode}`;
    fitModeBtn.querySelector('span').textContent = videoFitMode === 'cover' ? 'Cover' : 'Contain';
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

/* ==================== 键盘事件处理 ==================== */

/**
 * 处理键盘按键事件
 * 
 * 支持的快捷键：
 * - Escape: 退出全屏或返回上一页
 * - Space: 暂停/播放
 * - ArrowRight: 快进15秒
 * - ArrowLeft: 快退15秒
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
        forwardVideo();
    } else if (e.key === 'ArrowLeft') {
        rewindVideo();
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
 * 返回上一页
 * 
 * 清理定时器并跳转到首页。
 */
function goBack() {
    if (controlsTimeout) {
        clearTimeout(controlsTimeout);
    }
    window.location.href = '/';
}

/* ==================== 初始化 ==================== */

/**
 * 页面加载完成后初始化
 */
document.addEventListener('DOMContentLoaded', loadVideos);
