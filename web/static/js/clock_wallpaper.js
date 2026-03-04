let videos = [];
let shuffledIndices = [];
let currentShuffleIndex = 0;
let currentVideoIndex = -1;
let isPlaying = false;
let currentTime = 0;
let duration = 0;
let volume = 0;
let isMuted = true;
let showControls = true;
let hasStarted = false;
let isSwitchingVideo = false;
let isFullscreen = false;
let browseMode = false;
let currentSegment = 0;
let showClock = true;
let videoFitMode = 'cover';
let controlsTimeout = null;
let segmentTimeout = null;
let lastClickTime = 0;

const video = document.getElementById('videoPlayer');
const loadingScreen = document.getElementById('loadingScreen');
const playerContainer = document.getElementById('playerContainer');
const clockOverlay = document.getElementById('clockOverlay');
const clockTime = document.getElementById('clockTime');
const topBar = document.getElementById('topBar');
const controlsOverlay = document.getElementById('controlsOverlay');
const videoName = document.getElementById('videoName');
const videoCount = document.getElementById('videoCount');
const progressBar = document.getElementById('progressBar');
const currentTimeEl = document.getElementById('currentTime');
const durationEl = document.getElementById('duration');
const playBtn = document.getElementById('playBtn');
const skipBtn = document.getElementById('skipBtn');
const volumeBtn = document.getElementById('volumeBtn');
const volumeSlider = document.getElementById('volumeSlider');
const fullscreenBtn = document.getElementById('fullscreenBtn');
const clockToggleBtn = document.getElementById('clockToggleBtn');
const fitModeBtn = document.getElementById('fitModeBtn');
const browseModeBtn = document.getElementById('browseModeBtn');
const segmentIndicator = document.getElementById('segmentIndicator');

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

function playRandomVideo() {
    if (videos.length === 0) return;
    
    isSwitchingVideo = true;
    showControls = false;
    updateControlsVisibility();
    
    if (segmentTimeout) {
        clearTimeout(segmentTimeout);
    }
    
    currentSegment = 0;
    
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

function startSegmentPlayback(videoDuration) {
    const segmentDuration = videoDuration / 10;
    let currentSeg = 0;
    
    const playNextSegment = () => {
        if (currentSeg >= 10) {
            playRandomVideo();
            return;
        }
        
        const segmentStartTime = currentSeg * segmentDuration;
        video.currentTime = segmentStartTime;
        currentTime = segmentStartTime;
        
        if (video.paused) {
            video.play().catch(() => {});
        }
        
        segmentTimeout = setTimeout(() => {
            currentSeg++;
            currentSegment = currentSeg;
            segmentIndicator.textContent = `${currentSeg + 1}/10`;
            playNextSegment();
        }, 6000);
    };
    
    currentSegment = 0;
    segmentIndicator.textContent = '1/10';
    playNextSegment();
}

function setupEventListeners() {
    video.addEventListener('loadedmetadata', () => {
        duration = video.duration;
        progressBar.max = duration;
        durationEl.textContent = formatTime(duration);
        
        if (browseMode && video.duration > 60) {
            if (segmentTimeout) {
                clearTimeout(segmentTimeout);
            }
            setTimeout(() => {
                startSegmentPlayback(video.duration);
            }, 100);
        }
    });
    
    video.addEventListener('timeupdate', () => {
        if (!browseMode) {
            currentTime = video.currentTime;
            progressBar.value = currentTime;
            currentTimeEl.textContent = formatTime(currentTime);
        }
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
        if (browseMode && video.duration <= 60) {
            playRandomVideo();
            return;
        }
        if (!browseMode) {
            playRandomVideo();
        }
    });
    
    video.addEventListener('click', handleVideoClick);
    
    playBtn.addEventListener('click', togglePlay);
    skipBtn.addEventListener('click', playRandomVideo);
    volumeBtn.addEventListener('click', toggleMute);
    volumeSlider.addEventListener('input', handleVolumeChange);
    fullscreenBtn.addEventListener('click', toggleFullscreen);
    clockToggleBtn.addEventListener('click', toggleClock);
    fitModeBtn.addEventListener('click', toggleVideoFitMode);
    browseModeBtn.addEventListener('click', toggleBrowseMode);
    progressBar.addEventListener('input', handleSeek);
    
    playerContainer.addEventListener('mousemove', handleMouseMove);
    playerContainer.addEventListener('click', handleMouseMove);
    
    document.addEventListener('keydown', handleKeydown);
    document.addEventListener('fullscreenchange', handleFullscreenChange);
}

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

function togglePlay() {
    if (video.paused) {
        video.play();
    } else {
        video.pause();
    }
}

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

function handleVolumeChange(e) {
    volume = parseFloat(e.target.value);
    video.volume = volume;
    if (volume > 0) {
        isMuted = false;
        video.muted = false;
    }
    updateVolumeButton();
}

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

function handleSeek(e) {
    const newTime = parseFloat(e.target.value);
    video.currentTime = newTime;
    currentTime = newTime;
}

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

function handleFullscreenChange() {
    isFullscreen = !!document.fullscreenElement;
    updateFullscreenButton();
}

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

function toggleClock() {
    showClock = !showClock;
    clockOverlay.classList.toggle('hidden', !showClock);
    clockToggleBtn.classList.toggle('active', showClock);
}

function toggleVideoFitMode() {
    videoFitMode = videoFitMode === 'cover' ? 'contain' : 'cover';
    video.className = `video-player video-fit-${videoFitMode}`;
    fitModeBtn.querySelector('span').textContent = videoFitMode === 'cover' ? 'Cover' : 'Contain';
}

function toggleBrowseMode() {
    browseMode = !browseMode;
    browseModeBtn.classList.toggle('active', browseMode);
    
    if (browseMode) {
        segmentIndicator.style.display = 'inline';
    } else {
        segmentIndicator.style.display = 'none';
    }
    
    currentSegment = 0;
    
    if (segmentTimeout) {
        clearTimeout(segmentTimeout);
    }
    
    if (browseMode && video.duration > 60) {
        video.currentTime = 0;
        currentTime = 0;
        if (video.paused) {
            video.play().catch(() => {});
        }
        startSegmentPlayback(video.duration);
    } else if (!browseMode) {
        currentTime = video.currentTime;
    }
}

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

function updateControlsVisibility() {
    topBar.classList.toggle('hidden', !showControls);
    controlsOverlay.classList.toggle('hidden', !showControls);
}

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

function formatTime(time) {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

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

function goBack() {
    if (segmentTimeout) {
        clearTimeout(segmentTimeout);
    }
    if (controlsTimeout) {
        clearTimeout(controlsTimeout);
    }
    window.location.href = '/';
}

document.addEventListener('DOMContentLoaded', loadVideos);
