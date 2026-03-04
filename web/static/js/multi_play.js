let videos = [];
let players = [];
let shuffledIndices = [];
let currentIndices = [0, 0, 0, 0];
let currentVideoIds = [-1, -1, -1, -1];

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
            cell: document.getElementById(`cell${i}`)
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

function setupEventListeners() {
    players.forEach((player, index) => {
        player.video.addEventListener('ended', () => {
            playNextVideo(index);
        });
        
        player.video.addEventListener('error', () => {
            setTimeout(() => playNextVideo(index), 1000);
        });
        
        player.cell.addEventListener('click', () => {
            playNextVideo(index);
        });
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            goBack();
        }
    });
    
    let hideTimeout;
    const topBar = document.getElementById('topBar');
    
    multiPlayerContainer.addEventListener('mousemove', () => {
        topBar.classList.remove('hidden');
        clearTimeout(hideTimeout);
        hideTimeout = setTimeout(() => {
            topBar.classList.add('hidden');
        }, 2000);
    });
}

function goBack() {
    players.forEach(player => {
        player.video.pause();
        player.video.src = '';
    });
    window.location.href = '/';
}

document.addEventListener('DOMContentLoaded', loadVideos);
