/**
 * 视频标签管理系统 - 主应用入口
 * 
 * 重构说明：
 * - 所有功能已模块化到 modules/ 目录
 * - app.js 现在只负责初始化和协调各模块
 * - 全局函数保留用于 HTML 内联事件绑定
 */

import { appState } from './modules/stores/state.js';
import { fetchWithAuth, postJSON } from './modules/api/fetch.js';
import { showToast, showSuccess, showWarning, showError } from './modules/components/toast.js';
import { VideoPlayer, getMimeType, isNonNativeFormat } from './modules/components/video-player.js';
import { initTouchGestures, initSwipeToClose } from './modules/utils/touch.js';
import { sessionManager, initSessionTimeout } from './modules/utils/session.js';
import { shuffleArray } from './modules/utils/array.js';

import { 
    renderTagTree, 
    highlightActiveTag, 
    clearActiveTags 
} from './modules/ui/tag-tree.js';
import { 
    renderVideos, 
    showLoading, 
    showError as showVideoError 
} from './modules/ui/video-grid.js';
import { renderPagination } from './modules/ui/pagination.js';
import { 
    renderFilterTags, 
    updateSelectedTagsList, 
    clearFilterSelectionUI,
    renderCurrentFilter 
} from './modules/ui/filter-tags.js';
import { 
    openMobileSidebar, 
    closeMobileSidebar, 
    toggleMobileSidebar,
    openMobileSearch,
    closeMobileSearch,
    toggleMobileSearch,
    setupScrollHideNavbar
} from './modules/ui/mobile.js';

import { videoService } from './modules/services/video.js';
import { tagService } from './modules/services/tag.js';
import { statsService } from './modules/services/stats.js';

let videoPlayer = null;

function getPageSize() {
    return videoService.getPageSize();
}

function getCurrentPage() {
    return appState.get('currentPage');
}

function setCurrentPage(page) {
    appState.set('currentPage', page);
}

function getCurrentTagIds() {
    return appState.get('currentTagIds');
}

function setCurrentTagIds(ids) {
    appState.set('currentTagIds', ids);
}

function getAllTags() {
    return appState.get('allTags');
}

function setAllTags(tags) {
    appState.set('allTags', tags);
}

function getVideoPlayer() {
    return videoPlayer;
}

function setVideoPlayer(player) {
    videoPlayer = player;
}

function getCurrentVideoPath() {
    return appState.get('currentVideoPath');
}

function setCurrentVideoPath(path) {
    appState.set('currentVideoPath', path);
}

function getRandomSeed() {
    return appState.get('randomSeed');
}

function setRandomSeed(seed) {
    appState.set('randomSeed', seed);
}

function getIsRandomOrder() {
    return appState.get('isRandomOrder');
}

function setIsRandomOrder(value) {
    appState.set('isRandomOrder', value);
}

function getSelectedFilterTags() {
    return appState.get('selectedFilterTags');
}

function setSelectedFilterTags(tags) {
    appState.set('selectedFilterTags', tags);
}

function getSelectedFilterTagsByCategory() {
    return appState.get('selectedFilterTagsByCategory');
}

function setSelectedFilterTagsByCategory(obj) {
    appState.set('selectedFilterTagsByCategory', obj);
}

async function loadTagTree() {
    try {
        const tags = await tagService.loadTagTree();
        renderTagTree(tags);
    } catch (error) {
        document.getElementById('tagTree').innerHTML = '<div class="loading">加载失败</div>';
    }
}

async function loadVideos(page = 1) {
    setCurrentPage(page);
    showLoading('videoGrid');
    
    try {
        const data = await videoService.loadVideos(page);
        renderVideos(data.videos, 'videoGrid', { onVideoClick: playVideo });
        renderPagination(data, 'pagination', { onPageChange: loadVideos });
    } catch (error) {
        showVideoError('videoGrid');
    }
}

async function searchVideos() {
    const keyword = document.getElementById('searchInput').value.trim();
    
    if (!keyword) {
        loadVideos(1);
        return;
    }
    
    setCurrentTagIds([]);
    document.getElementById('currentFilter').style.display = 'none';
    showLoading('videoGrid', '搜索中...');
    
    try {
        const data = await videoService.searchVideos(keyword);
        renderVideos(data.videos, 'videoGrid', { onVideoClick: playVideo });
        renderPagination(data, 'pagination', { onPageChange: loadVideos });
        
        document.getElementById('currentFilter').style.display = 'flex';
        document.getElementById('filterTags').innerHTML = `
            <span class="filter-tag">搜索: "${keyword}"</span>
        `;
    } catch (error) {
        showVideoError('videoGrid', '搜索失败');
    }
}

async function mobileSearchVideos() {
    const keyword = document.getElementById('mobileSearchInput').value.trim();
    
    if (!keyword) {
        loadVideos(1);
        closeMobileSearch();
        return;
    }
    
    setCurrentTagIds([]);
    document.getElementById('currentFilter').style.display = 'none';
    showLoading('videoGrid', '搜索中...');
    
    try {
        const data = await videoService.searchVideos(keyword);
        renderVideos(data.videos, 'videoGrid', { onVideoClick: playVideo });
        renderPagination(data, 'pagination', { onPageChange: loadVideos });
        
        document.getElementById('currentFilter').style.display = 'flex';
        document.getElementById('filterTags').innerHTML = `
            <span class="filter-tag">搜索: "${keyword}"</span>
        `;
        closeMobileSearch();
    } catch (error) {
        showVideoError('videoGrid', '搜索失败');
        closeMobileSearch();
    }
}

function filterByTag(tagId, tagName) {
    highlightActiveTag(tagId);
    
    setCurrentTagIds([tagId]);
    setSelectedFilterTagsByCategory({});
    setIsRandomOrder(false);
    setRandomSeed(Date.now());
    
    const filterContainer = document.getElementById('currentFilter');
    filterContainer.style.display = 'flex';
    document.getElementById('filterTags').innerHTML = `
        <span class="filter-tag">${tagName}</span>
    `;
    
    closeMobileSidebar();
    loadVideos(1);
}

function clearFilter() {
    setCurrentTagIds([]);
    setSelectedFilterTags([]);
    setSelectedFilterTagsByCategory({});
    setRandomSeed(Date.now());
    setIsRandomOrder(false);
    
    clearActiveTags();
    
    document.getElementById('currentFilter').style.display = 'none';
    document.getElementById('clockWallpaperBtn').disabled = true;
    document.getElementById('multiPlayBtn').disabled = true;
    document.getElementById('randomRecommendBtn').disabled = true;
    document.getElementById('shuffleBtn').disabled = true;
    loadVideos(1);
}

async function loadStats() {
    try {
        const stats = await statsService.loadStats();
        statsService.updateVideoCount(stats.video_count);
    } catch (error) {
        console.error('加载统计信息失败:', error);
    }
}

async function playVideo(videoIdOrVideo, title, tags, filePath) {
    try {
        let videoId, videoTitle, videoTags, videoFilePath;
        
        if (typeof videoIdOrVideo === 'object' && videoIdOrVideo !== null) {
            videoId = videoIdOrVideo.id;
            videoTitle = videoIdOrVideo.title;
            videoTags = videoIdOrVideo.tags;
            videoFilePath = videoIdOrVideo.file_path;
        } else {
            videoId = videoIdOrVideo;
            videoTitle = title;
            videoTags = tags;
            videoFilePath = filePath;
        }
        
        setCurrentVideoPath(videoFilePath);
        
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
        
        const player = videojs('videoPlayer', playerOptions);
        setVideoPlayer(player);
        
        getVideoPlayer().src({
            src: data.stream_url,
            type: getMimeType(fileExt)
        });
        
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
        
        if (isMobile) {
            modal.classList.add('mobile-mode');
        }
        
        getVideoPlayer().ready(function() {
            this.play().catch(function(error) {
                console.log('自动播放失败，请手动点击播放:', error);
            });
            
            if (isMobile) {
                this.on('fullscreenchange', function() {
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
    } catch (error) {
        console.error('获取视频信息失败:', error);
        showToast('无法播放视频: ' + error.message, 'error');
    }
}

function closeVideoModal() {
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

function openAdvancedFilter() {
    const modal = document.getElementById('advancedFilterModal');
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    renderFilterTags(getAllTags());
}

function closeAdvancedFilter() {
    const modal = document.getElementById('advancedFilterModal');
    modal.classList.remove('show');
    document.body.style.overflow = '';
}

function clearFilterSelection() {
    clearFilterSelectionUI();
}

async function applyAdvancedFilter() {
    const filterTags = getSelectedFilterTags();
    const filterTagsByCategory = getSelectedFilterTagsByCategory();
    const tags = getAllTags();
    
    if (filterTags.length === 0) {
        showToast('请至少选择一个标签');
        return;
    }
    
    closeAdvancedFilter();
    
    setCurrentTagIds([...filterTags]);
    setCurrentPage(1);
    setIsRandomOrder(false);
    setRandomSeed(Date.now());
    
    const filterContainer = document.getElementById('currentFilter');
    renderCurrentFilter(filterTagsByCategory, tags);
    filterContainer.style.display = 'flex';
    
    document.getElementById('clockWallpaperBtn').disabled = false;
    document.getElementById('multiPlayBtn').disabled = false;
    document.getElementById('randomRecommendBtn').disabled = false;
    document.getElementById('shuffleBtn').disabled = false;
    
    await loadVideosByTagsAdvanced(filterTagsByCategory, false);
}

async function shuffleVideos() {
    const filterTagsByCategory = getSelectedFilterTagsByCategory();
    
    if (Object.keys(filterTagsByCategory).length === 0) {
        return;
    }
    
    const shuffleBtn = document.getElementById('shuffleBtn');
    shuffleBtn.classList.add('shuffling');
    
    setRandomSeed(Date.now());
    setIsRandomOrder(true);
    setCurrentPage(1);
    
    await loadVideosByTagsAdvanced(filterTagsByCategory, true);
    
    setTimeout(() => {
        shuffleBtn.classList.remove('shuffling');
    }, 300);
}

async function loadVideosByTagsAdvanced(tagsByCategory, shuffle = false) {
    showLoading('videoGrid');
    
    try {
        const data = await videoService.loadVideosByTagsAdvanced(tagsByCategory, shuffle);
        renderVideos(data.videos, 'videoGrid', { onVideoClick: playVideo });
        renderPagination(data, 'pagination', { onPageChange: (page) => {
            setCurrentPage(page);
            loadVideosByTagsAdvanced(getSelectedFilterTagsByCategory(), false);
        }});
    } catch (error) {
        showVideoError('videoGrid');
    }
}

function goToAdvancedFilterPage(page) {
    setCurrentPage(page);
    loadVideosByTagsAdvanced(getSelectedFilterTagsByCategory(), false);
}

function openClockWallpaper() {
    if (Object.keys(getSelectedFilterTagsByCategory()).length === 0) {
        showToast('请先进行多级筛选');
        return;
    }
    
    const params = encodeURIComponent(JSON.stringify(getSelectedFilterTagsByCategory()));
    window.location.href = `/clock-wallpaper?filter=${params}`;
}

function openMultiPlay() {
    if (Object.keys(getSelectedFilterTagsByCategory()).length === 0) {
        showToast('请先进行多级筛选');
        return;
    }
    
    const params = encodeURIComponent(JSON.stringify(getSelectedFilterTagsByCategory()));
    window.location.href = `/multi-play?filter=${params}`;
}

function openRandomRecommend() {
    if (Object.keys(getSelectedFilterTagsByCategory()).length === 0) {
        showToast('请先进行多级筛选');
        return;
    }
    
    const params = encodeURIComponent(JSON.stringify(getSelectedFilterTagsByCategory()));
    window.location.href = `/random-recommend?filter=${params}`;
}

function logout(timeout = false) {
    if (timeout) {
        alert('由于长时间未操作，您已自动退出登录');
    }
    window.location.href = '/logout';
}

function toggleFullscreen() {
    const elem = document.documentElement;
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    
    if (!document.fullscreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement) {
        if (elem.requestFullscreen) {
            elem.requestFullscreen();
        } else if (elem.webkitRequestFullscreen) {
            elem.webkitRequestFullscreen();
        } else if (elem.msRequestFullscreen) {
            elem.msRequestFullscreen();
        } else if (elem.mozRequestFullScreen) {
            elem.mozRequestFullScreen();
        }
        
        if (fullscreenBtn) {
            fullscreenBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/>
                </svg>
            `;
            fullscreenBtn.title = '退出全屏';
        }
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        } else if (document.mozCancelFullScreen) {
            document.mozCancelFullScreen();
        }
        
        if (fullscreenBtn) {
            fullscreenBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                </svg>
            `;
            fullscreenBtn.title = '全屏模式';
        }
    }
}

function updateFullscreenButton() {
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const isFullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement);
    
    if (fullscreenBtn) {
        if (isFullscreen) {
            fullscreenBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/>
                </svg>
            `;
            fullscreenBtn.title = '退出全屏';
        } else {
            fullscreenBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                </svg>
            `;
            fullscreenBtn.title = '全屏模式';
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadTagTree();
    loadVideos();
    loadStats();
    
    initSessionTimeout({
        onTimeout: () => logout(true),
        onWarning: (seconds) => {
            const minutes = Math.floor(seconds / 60);
            const secs = seconds % 60;
            showToast(`会话将在 ${minutes}分${secs}秒 后过期，请继续操作以保持登录`, 'warning');
        }
    });
    
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchVideos();
        }
    });
    
    const mobileSearchInput = document.getElementById('mobileSearchInput');
    if (mobileSearchInput) {
        mobileSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                mobileSearchVideos();
            }
        });
    }
    
    initTouchGestures({
        onSwipeRight: openMobileSidebar,
        onSwipeLeft: closeMobileSidebar,
        edgeThreshold: 30
    });
    
    initSwipeToClose('.video-player-modal, .advanced-filter-modal', () => {
        const videoModal = document.getElementById('videoModal');
        if (videoModal && videoModal.classList.contains('show')) {
            closeVideoModal();
        } else {
            closeAdvancedFilter();
        }
    });
    
    setupScrollHideNavbar();
    
    document.addEventListener('tag-selected', (e) => {
        filterByTag(e.detail.tagId, e.detail.tagName);
    });
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeVideoModal();
        closeAdvancedFilter();
        closeMobileSidebar();
        closeMobileSearch();
    }
});

document.addEventListener('fullscreenchange', updateFullscreenButton);
document.addEventListener('webkitfullscreenchange', updateFullscreenButton);
document.addEventListener('msfullscreenchange', updateFullscreenButton);
document.addEventListener('mozfullscreenchange', updateFullscreenButton);

document.addEventListener('DOMContentLoaded', function() {
    const videoModal = document.getElementById('videoModal');
    const modalContent = videoModal.querySelector('.modal-content');
    
    videoModal.addEventListener('click', function(e) {
        if (e.target === videoModal) {
            e.stopPropagation();
        }
    });
    
    modalContent.addEventListener('click', function(e) {
        e.stopPropagation();
    });
});

window.loadTagTree = loadTagTree;
window.loadVideos = loadVideos;
window.searchVideos = searchVideos;
window.mobileSearchVideos = mobileSearchVideos;
window.filterByTag = filterByTag;
window.clearFilter = clearFilter;
window.playVideo = playVideo;
window.closeVideoModal = closeVideoModal;
window.openAdvancedFilter = openAdvancedFilter;
window.closeAdvancedFilter = closeAdvancedFilter;
window.clearFilterSelection = clearFilterSelection;
window.applyAdvancedFilter = applyAdvancedFilter;
window.shuffleVideos = shuffleVideos;
window.goToAdvancedFilterPage = goToAdvancedFilterPage;
window.openClockWallpaper = openClockWallpaper;
window.openMultiPlay = openMultiPlay;
window.openRandomRecommend = openRandomRecommend;
window.toggleMobileSidebar = toggleMobileSidebar;
window.openMobileSidebar = openMobileSidebar;
window.closeMobileSidebar = closeMobileSidebar;
window.toggleMobileSearch = toggleMobileSearch;
window.openMobileSearch = openMobileSearch;
window.closeMobileSearch = closeMobileSearch;
window.showToast = showToast;
window.logout = logout;
window.toggleFullscreen = toggleFullscreen;

export {
    appState,
    loadTagTree,
    loadVideos,
    searchVideos,
    filterByTag,
    clearFilter,
    playVideo,
    closeVideoModal,
    openAdvancedFilter,
    closeAdvancedFilter,
    applyAdvancedFilter,
    shuffleVideos
};
