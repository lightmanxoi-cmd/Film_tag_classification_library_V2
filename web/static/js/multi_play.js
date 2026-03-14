/**
 * 四分屏视频播放器
 * 
 * 本文件实现了一个四分屏同时播放的视频播放器，具有以下特点：
 * - 同时播放四个视频，每个视频独立控制
 * - 支持随机播放，避免四个播放器播放同一视频
 * - 支持单独控制每个播放器的播放、暂停、音量
 * - 支持全局静音切换
 * - 支持时钟叠加显示
 * - 自动隐藏控制栏
 * 
 * 主要功能模块：
 * 1. 视频加载模块：loadVideos、initAllShuffledIndices、initPlayers
 * 2. 播放控制模块：playNextVideo、togglePlay、getNextAvailableIndex
 * 3. 音量控制模块：setVolume、toggleMute、toggleAllMute
 * 4. 进度控制模块：seekVideo、updateTimeDisplay
 * 5. 时钟显示模块：startClock、toggleClockDisplay
 * 
 * 作者：Video Library System
 * 创建时间：2024
 */

/* ==================== 全局变量定义 ==================== */

/** 视频列表数据 */
let videos = [];

/** 四个播放器实例数组 */
let players = [];

/** 每个播放器独立的随机打乱后的视频索引数组（二维数组） */
let shuffledIndicesArray = [[], [], [], []];

/** 每个播放器当前的随机索引位置 */
let currentIndices = [0, 0, 0, 0];

/** 每个播放器当前播放的视频ID */
let currentVideoIds = [-1, -1, -1, -1];

/** 控制栏自动隐藏的定时器 */
let hideControlsTimeout = null;

/** 每个播放器的单击定时器（用于区分单击和双击） */
let clickTimers = [null, null, null, null];

/** 每个播放器的上次点击时间 */
let lastClickTime = [0, 0, 0, 0];

/** 是否全部静音 */
let allMuted = true;

/** 是否显示时钟 */
let showClock = false;

/* ==================== DOM 元素引用 ==================== */

/** 加载屏幕元素 */
const loadingScreen = document.getElementById('loadingScreen');

/** 多播放器容器元素 */
const multiPlayerContainer = document.getElementById('multiPlayerContainer');

/** 视频数量显示元素 */
const videoCount = document.getElementById('videoCount');

/** 时钟叠加层元素 */
const clockOverlay = document.getElementById('clockOverlay');

/** 时钟时间显示元素 */
const clockTime = document.getElementById('clockTime');

/** 时钟切换按钮 */
const clockToggleBtn = document.getElementById('clockToggleBtn');

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
 * 加载成功后初始化四个播放器并开始播放。
 */
async function loadVideos() {
    const tagsByCategory = getUrlParams();
    
    if (!tagsByCategory) {
        alert('No filter parameters found');
        window.location.href = '/';
        return;
    }
    
    try {
        const randomSeed = Date.now();
        const response = await fetchWithAuth('/api/videos/by-tags-advanced', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tags_by_category: tagsByCategory,
                page: 1,
                page_size: 1000,
                random_order: true,
                random_seed: randomSeed
            })
        });
        
        const result = await response.json();
        
        if (result.success && result.data.videos.length >= 4) {
            videos = result.data.videos;
            videoCount.textContent = `${videos.length} videos`;
            
            initAllShuffledIndices();
            initPlayers();
            
            loadingScreen.style.display = 'none';
            multiPlayerContainer.style.display = 'block';
            
            startAllPlayers();
            startClock();
            setupEventListeners();
        } else if (result.success && result.data.videos.length > 0) {
            videos = result.data.videos;
            videoCount.textContent = `${videos.length} videos`;
            
            initAllShuffledIndices();
            initPlayers();
            
            loadingScreen.style.display = 'none';
            multiPlayerContainer.style.display = 'block';
            
            startAllPlayers();
            startClock();
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
 * 初始化指定播放器的随机播放索引
 * 
 * 为指定播放器创建独立的视频索引数组并使用 Fisher-Yates 算法进行随机打乱。
 * 
 * @param {number} playerIndex - 播放器索引（0-3）
 */
function initShuffledIndices(playerIndex) {
    const indices = [];
    for (let i = 0; i < videos.length; i++) {
        indices.push(i);
    }
    for (let i = indices.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [indices[i], indices[j]] = [indices[j], indices[i]];
    }
    shuffledIndicesArray[playerIndex] = indices;
}

/**
 * 初始化所有播放器的随机播放索引
 * 
 * 为四个播放器分别创建独立的随机索引数组。
 */
function initAllShuffledIndices() {
    for (let i = 0; i < 4; i++) {
        initShuffledIndices(i);
    }
}

/**
 * 初始化四个播放器
 * 
 * 为每个播放器获取对应的DOM元素引用，包括视频元素、标题、控制按钮等。
 */
function initPlayers() {
    players = [];
    for (let i = 0; i < 4; i++) {
        players.push({
            video: document.getElementById(`video${i}`),
            title: document.getElementById(`title${i}`),
            cell: document.getElementById(`cell${i}`),
            playBtn: document.querySelector(`.play-btn[data-player="${i}"]`),
            skipBtn: document.querySelector(`.skip-btn[data-player="${i}"]`),
            progressBar: document.querySelector(`.progress-bar[data-player="${i}"]`),
            timeDisplay: document.querySelector(`.time-display[data-player="${i}"]`),
            volumeBtn: document.querySelector(`.volume-btn[data-player="${i}"]`),
            volumeSlider: document.querySelector(`.volume-slider[data-player="${i}"]`)
        });
    }
}

/**
 * 启动所有播放器
 * 
 * 为四个播放器分别加载并播放第一个视频。
 */
function startAllPlayers() {
    for (let i = 0; i < 4; i++) {
        playNextVideo(i);
    }
}

/* ==================== 视频选择逻辑 ==================== */

/**
 * 获取下一个可用的视频索引
 * 
 * 从该播放器独立的随机索引数组中获取下一个视频，确保不与其他播放器正在播放的视频重复。
 * 如果所有视频都已被播放过，则重新为该播放器生成随机索引数组。
 * 
 * @param {number} playerIndex - 播放器索引（0-3）
 * @returns {number} 视频在原数组中的索引
 */
function getNextAvailableIndex(playerIndex) {
    const otherPlayingIds = currentVideoIds.filter((id, idx) => idx !== playerIndex);
    const shuffledIndices = shuffledIndicesArray[playerIndex];
    
    let attempts = 0;
    const maxAttempts = videos.length;
    
    while (attempts < maxAttempts) {
        if (currentIndices[playerIndex] >= shuffledIndices.length) {
            initShuffledIndices(playerIndex);
            currentIndices[playerIndex] = 0;
        }
        
        const videoIndex = shuffledIndicesArray[playerIndex][currentIndices[playerIndex]];
        const videoId = videos[videoIndex].id;
        
        if (!otherPlayingIds.includes(videoId)) {
            currentIndices[playerIndex]++;
            return videoIndex;
        }
        
        currentIndices[playerIndex]++;
        attempts++;
    }
    
    return shuffledIndicesArray[playerIndex][0];
}

/**
 * 播放下一个视频
 * 
 * 为指定播放器加载并播放下一个视频。
 * 
 * @param {number} playerIndex - 播放器索引（0-3）
 */
function playNextVideo(playerIndex) {
    if (videos.length === 0) return;
    
    const videoIndex = getNextAvailableIndex(playerIndex);
    const videoData = videos[videoIndex];
    const player = players[playerIndex];
    
    currentVideoIds[playerIndex] = videoData.id;
    
    player.video.src = `/video/stream/${videoData.id}`;
    player.title.textContent = videoData.title;
    
    player.video.load();
    player.video.play().catch(() => {});
}

/* ==================== 播放控制函数 ==================== */

/**
 * 切换播放/暂停状态
 * 
 * @param {number} playerIndex - 播放器索引（0-3）
 */
function togglePlay(playerIndex) {
    const player = players[playerIndex];
    if (player.video.paused) {
        player.video.play();
    } else {
        player.video.pause();
    }
}

/**
 * 更新播放按钮图标
 * 
 * 根据当前播放状态更新按钮显示的图标（播放或暂停）。
 * 
 * @param {number} playerIndex - 播放器索引（0-3）
 */
function updatePlayButton(playerIndex) {
    const player = players[playerIndex];
    if (player.video.paused) {
        player.playBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
    } else {
        player.playBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/></svg>';
    }
}

/* ==================== 工具函数 ==================== */

/**
 * 格式化时间显示
 * 
 * 将秒数转换为 分:秒 格式。
 * 
 * @param {number} seconds - 时间（秒）
 * @returns {string} 格式化后的时间字符串
 */
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * 更新时间显示
 * 
 * 更新指定播放器的时间显示（当前时间 / 总时长）。
 * 
 * @param {number} playerIndex - 播放器索引（0-3）
 */
function updateTimeDisplay(playerIndex) {
    const player = players[playerIndex];
    const current = player.video.currentTime;
    const dur = player.video.duration || 0;
    player.timeDisplay.textContent = `${formatTime(current)} / ${formatTime(dur)}`;
}

/* ==================== 进度控制函数 ==================== */

/**
 * 跳转视频进度
 * 
 * 根据进度条百分比值跳转到视频对应位置。
 * 
 * @param {number} playerIndex - 播放器索引（0-3）
 * @param {number} value - 进度条值（0-100）
 */
function seekVideo(playerIndex, value) {
    const player = players[playerIndex];
    const dur = player.video.duration || 0;
    player.video.currentTime = (value / 100) * dur;
}

/* ==================== 音量控制函数 ==================== */

/**
 * 设置音量
 * 
 * 设置指定播放器的音量值，并更新音量滑块和按钮状态。
 * 
 * @param {number} playerIndex - 播放器索引（0-3）
 * @param {number} value - 音量值（0-1）
 */
function setVolume(playerIndex, value) {
    const player = players[playerIndex];
    player.video.volume = value;
    player.video.muted = value === 0;
    player.volumeSlider.value = value;
    updateVolumeButton(playerIndex);
}

/**
 * 切换静音状态
 * 
 * 切换指定播放器的静音状态。
 * 如果当前静音，则恢复音量到0.5；否则静音。
 * 
 * @param {number} playerIndex - 播放器索引（0-3）
 */
function toggleMute(playerIndex) {
    const player = players[playerIndex];
    if (player.video.muted || player.video.volume === 0) {
        setVolume(playerIndex, 0.5);
    } else {
        setVolume(playerIndex, 0);
    }
}

/**
 * 更新音量按钮图标
 * 
 * 根据当前音量和静音状态显示不同的图标。
 * 
 * @param {number} playerIndex - 播放器索引（0-3）
 */
function updateVolumeButton(playerIndex) {
    const player = players[playerIndex];
    const vol = player.video.muted ? 0 : player.video.volume;
    
    if (vol === 0) {
        player.volumeBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/></svg>';
    } else if (vol < 0.5) {
        player.volumeBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM5 9v6h4l5 5V4L9 9H5z"/></svg>';
    } else {
        player.volumeBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>';
    }
}

/**
 * 切换全部静音
 * 
 * 同时切换所有四个播放器的静音状态。
 */
function toggleAllMute() {
    allMuted = !allMuted;
    players.forEach((player, index) => {
        if (allMuted) {
            player.video.muted = true;
            player.volumeSlider.value = 0;
        } else {
            player.video.muted = false;
            player.video.volume = 0.5;
            player.volumeSlider.value = 0.5;
        }
        updateVolumeButton(index);
    });
}

/* ==================== 时钟显示功能 ==================== */

/**
 * 切换时钟显示
 */
function toggleClockDisplay() {
    showClock = !showClock;
    clockOverlay.classList.toggle('hidden', !showClock);
    clockToggleBtn.classList.toggle('active', showClock);
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

/* ==================== 事件监听器设置 ==================== */

/**
 * 设置所有事件监听器
 * 
 * 为四个播放器和控制按钮绑定各种事件处理函数。
 */
function setupEventListeners() {
    players.forEach((player, index) => {
        player.video.addEventListener('ended', () => {
            playNextVideo(index);
        });
        
        player.video.addEventListener('error', () => {
            setTimeout(() => playNextVideo(index), 1000);
        });
        
        player.video.addEventListener('play', () => {
            updatePlayButton(index);
        });
        
        player.video.addEventListener('pause', () => {
            updatePlayButton(index);
        });
        
        player.video.addEventListener('timeupdate', () => {
            const dur = player.video.duration || 0;
            if (dur > 0) {
                const progress = (player.video.currentTime / dur) * 100;
                player.progressBar.value = progress;
            }
            updateTimeDisplay(index);
        });
        
        player.video.addEventListener('loadedmetadata', () => {
            updateTimeDisplay(index);
        });
        
        player.playBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            togglePlay(index);
        });
        
        player.skipBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            playNextVideo(index);
        });
        
        player.progressBar.addEventListener('input', (e) => {
            e.stopPropagation();
            seekVideo(index, parseFloat(e.target.value));
        });
        
        player.volumeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleMute(index);
        });
        
        player.volumeSlider.addEventListener('input', (e) => {
            e.stopPropagation();
            setVolume(index, parseFloat(e.target.value));
        });
        
        player.cell.addEventListener('click', (e) => {
            if (e.target.closest('.control-bar')) return;
            
            const now = Date.now();
            const timeDiff = now - lastClickTime[index];
            lastClickTime[index] = now;
            
            if (timeDiff < 300) {
                if (clickTimers[index]) {
                    clearTimeout(clickTimers[index]);
                    clickTimers[index] = null;
                }
                togglePlay(index);
            } else {
                clickTimers[index] = setTimeout(() => {
                    playNextVideo(index);
                    clickTimers[index] = null;
                }, 300);
            }
        });
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            goBack();
        } else if (e.key.toLowerCase() === 'm') {
            toggleAllMute();
        }
    });
    
    const topBar = document.getElementById('topBar');
    
    /**
     * 显示所有控制栏
     * 
     * 显示顶部栏和每个播放器的控制栏，1秒后自动隐藏。
     */
    function showAllControls() {
        topBar.classList.remove('hidden');
        players.forEach(player => {
            player.cell.querySelector('.control-bar').classList.remove('hidden');
            player.cell.querySelector('.video-overlay').classList.remove('hidden');
        });
        clearTimeout(hideControlsTimeout);
        hideControlsTimeout = setTimeout(() => {
            topBar.classList.add('hidden');
            players.forEach(player => {
                player.cell.querySelector('.control-bar').classList.add('hidden');
                player.cell.querySelector('.video-overlay').classList.add('hidden');
            });
        }, 1000);
    }
    
    multiPlayerContainer.addEventListener('mousemove', showAllControls);
    multiPlayerContainer.addEventListener('click', showAllControls);
    
    showAllControls();
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
 * 暂停所有播放器并跳转到首页。
 */
function goBack() {
    players.forEach(player => {
        player.video.pause();
        player.video.src = '';
    });
    stopSessionKeepAlive();
    window.location.href = '/';
}

/* ==================== 初始化 ==================== */

/**
 * 页面加载完成后初始化
 */
document.addEventListener('DOMContentLoaded', () => {
    loadVideos();
    startSessionKeepAlive();
});
