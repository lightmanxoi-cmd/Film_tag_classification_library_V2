let videos = [];
let players = [];
let shuffledIndices = [];
let currentIndices = [0, 0, 0, 0];
let currentVideoIds = [-1, -1, -1, -1];
let hideControlsTimeout = null;

const loadingScreen = document.getElementById('loadingScreen');
const multiPlayerContainer = document.getElementById('multiPlayerContainer');
const videoCount = document.getElementById('videoCount');

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
        
        if (result.success && result.data.videos.length >= 4) {
            videos = result.data.videos;
            videoCount.textContent = `${videos.length} videos`;
            
            initShuffledIndices();
            initPlayers();
            
            loadingScreen.style.display = 'none';
            multiPlayerContainer.style.display = 'block';
            
            startAllPlayers();
            setupEventListeners();
        } else if (result.success && result.data.videos.length > 0) {
            videos = result.data.videos;
            videoCount.textContent = `${videos.length} videos`;
            
            initShuffledIndices();
            initPlayers();
            
            loadingScreen.style.display = 'none';
            multiPlayerContainer.style.display = 'block';
            
            startAllPlayers();
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
}

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

function startAllPlayers() {
    for (let i = 0; i < 4; i++) {
        playNextVideo(i);
    }
}

function getNextAvailableIndex(playerIndex) {
    const otherPlayingIds = currentVideoIds.filter((id, idx) => idx !== playerIndex);
    
    let attempts = 0;
    const maxAttempts = videos.length;
    
    while (attempts < maxAttempts) {
        if (currentIndices[playerIndex] >= shuffledIndices.length) {
            initShuffledIndices();
            currentIndices[playerIndex] = 0;
        }
        
        const videoIndex = shuffledIndices[currentIndices[playerIndex]];
        const videoId = videos[videoIndex].id;
        
        if (!otherPlayingIds.includes(videoId)) {
            currentIndices[playerIndex]++;
            return videoIndex;
        }
        
        currentIndices[playerIndex]++;
        attempts++;
    }
    
    return shuffledIndices[0];
}

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

function togglePlay(playerIndex) {
    const player = players[playerIndex];
    if (player.video.paused) {
        player.video.play();
    } else {
        player.video.pause();
    }
}

function updatePlayButton(playerIndex) {
    const player = players[playerIndex];
    if (player.video.paused) {
        player.playBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
    } else {
        player.playBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/></svg>';
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function updateTimeDisplay(playerIndex) {
    const player = players[playerIndex];
    const current = player.video.currentTime;
    const dur = player.video.duration || 0;
    player.timeDisplay.textContent = `${formatTime(current)} / ${formatTime(dur)}`;
}

function seekVideo(playerIndex, value) {
    const player = players[playerIndex];
    const dur = player.video.duration || 0;
    player.video.currentTime = (value / 100) * dur;
}

function setVolume(playerIndex, value) {
    const player = players[playerIndex];
    player.video.volume = value;
    player.video.muted = value === 0;
    player.volumeSlider.value = value;
    updateVolumeButton(playerIndex);
}

function toggleMute(playerIndex) {
    const player = players[playerIndex];
    if (player.video.muted || player.video.volume === 0) {
        setVolume(playerIndex, 0.5);
    } else {
        setVolume(playerIndex, 0);
    }
}

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
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            goBack();
        }
    });
    
    const topBar = document.getElementById('topBar');
    
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

function goBack() {
    players.forEach(player => {
        player.video.pause();
        player.video.src = '';
    });
    window.location.href = '/';
}

document.addEventListener('DOMContentLoaded', loadVideos);
