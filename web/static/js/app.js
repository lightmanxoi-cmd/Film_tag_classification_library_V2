import { appState } from './modules/stores/state.js';
import { showToast } from './modules/components/toast.js';
import { initTouchGestures, initSwipeToClose } from './modules/utils/touch.js';
import { initSessionTimeout } from './modules/utils/session.js';

import { renderTagTree } from './modules/ui/tag-tree.js';
import { renderVideos, showLoading, showError as showVideoError } from './modules/ui/video-grid.js';
import { renderPagination } from './modules/ui/pagination.js';
import { tagService } from './modules/services/tag.js';
import { videoService } from './modules/services/video.js';
import { statsService } from './modules/services/stats.js';
import {
    openMobileSidebar,
    closeMobileSidebar,
    toggleMobileSidebar,
    openMobileSearch,
    closeMobileSearch,
    toggleMobileSearch,
    setupScrollHideNavbar
} from './modules/ui/mobile.js';

import { playVideo, closeVideoModal } from './modules/controllers/video-play-controller.js';
import {
    filterByTag,
    clearFilter,
    openAdvancedFilter,
    closeAdvancedFilter,
    clearFilterSelection,
    applyAdvancedFilter,
    shuffleVideos,
    goToAdvancedFilterPage,
    openClockWallpaper,
    openMultiPlay,
    openRandomRecommend,
    openVideoImport,
    logout
} from './modules/controllers/filter-controller.js';
import { searchVideos, mobileSearchVideos } from './modules/controllers/search-controller.js';
import { toggleFullscreen, initFullscreenListeners } from './modules/controllers/ui-controller.js';

async function loadTagTree() {
    try {
        const tags = await tagService.loadTagTree();
        renderTagTree(tags);
    } catch (error) {
        document.getElementById('tagTree').innerHTML = '<div class="loading">加载失败</div>';
    }
}

async function loadVideos(page = 1) {
    appState.set('currentPage', page);
    showLoading('videoGrid');

    try {
        const data = await videoService.loadVideos(page);
        renderVideos(data.videos, 'videoGrid', { onVideoClick: playVideo });
        renderPagination(data, 'pagination', { onPageChange: loadVideos });
    } catch (error) {
        showVideoError('videoGrid');
    }
}

async function loadStats() {
    try {
        const stats = await statsService.loadStats();
        statsService.updateVideoCount(stats.video_count);
    } catch (error) {
        console.error('加载统计信息失败:', error);
    }
}

const actionHandlers = {
    'toggle-mobile-sidebar': () => toggleMobileSidebar(),
    'close-mobile-sidebar': () => closeMobileSidebar(),
    'toggle-mobile-search': () => toggleMobileSearch(),
    'close-mobile-search': () => closeMobileSearch(),
    'open-advanced-filter': () => openAdvancedFilter(),
    'close-advanced-filter': () => closeAdvancedFilter(),
    'clear-filter': () => clearFilter(playVideo),
    'clear-filter-selection': () => clearFilterSelection(),
    'apply-advanced-filter': () => applyAdvancedFilter(playVideo),
    'shuffle-videos': () => shuffleVideos(playVideo),
    'open-clock-wallpaper': () => openClockWallpaper(),
    'open-multi-play': () => openMultiPlay(),
    'open-random-recommend': () => openRandomRecommend(),
    'open-video-import': () => openVideoImport(),
    'search-videos': () => searchVideos(playVideo),
    'mobile-search-videos': () => mobileSearchVideos(playVideo),
    'close-video-modal': () => closeVideoModal(),
    'toggle-fullscreen': () => toggleFullscreen(),
    'logout': () => logout(),
    'electron-minimize': () => window.electronAPI?.minimize(),
    'electron-maximize': () => window.electronAPI?.maximize(),
    'electron-close': () => window.electronAPI?.close()
};

function initDeclarativeEvents() {
    document.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action]');
        if (!target) return;

        const action = target.dataset.action;
        const handler = actionHandlers[action];
        if (handler) {
            e.preventDefault();
            handler(e);
        }
    });
}

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeVideoModal();
            closeAdvancedFilter();
            closeMobileSidebar();
            closeMobileSearch();
        }
    });
}

function initSearchInputListeners() {
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchVideos(playVideo);
        }
    });

    const mobileSearchInput = document.getElementById('mobileSearchInput');
    if (mobileSearchInput) {
        mobileSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                mobileSearchVideos(playVideo);
            }
        });
    }
}

function initTouchListeners() {
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
}

function initTagSelectedListener() {
    document.addEventListener('tag-selected', (e) => {
        filterByTag(e.detail.tagId, e.detail.tagName, playVideo);
    });
}

function initVideoModalClickOutside() {
    const videoModal = document.getElementById('videoModal');
    const modalContent = videoModal.querySelector('.modal-content');

    videoModal.addEventListener('click', (e) => {
        if (e.target === videoModal) {
            e.stopPropagation();
        }
    });

    modalContent.addEventListener('click', (e) => {
        e.stopPropagation();
    });
}

function initElectronMode() {
    if (window.electronAPI && window.electronAPI.isElectron) {
        document.body.classList.add('electron-mode');
        console.log('[Electron] Running in Electron mode');
    }
}

document.addEventListener('DOMContentLoaded', function () {
    loadTagTree();
    loadVideos();
    loadStats();

    initSessionTimeout();
    initDeclarativeEvents();
    initKeyboardShortcuts();
    initSearchInputListeners();
    initTouchListeners();
    initTagSelectedListener();
    initVideoModalClickOutside();
    initFullscreenListeners();
    setupScrollHideNavbar();
    initElectronMode();
});

window.loadTagTree = loadTagTree;
window.loadVideos = loadVideos;
window.searchVideos = () => searchVideos(playVideo);
window.mobileSearchVideos = () => mobileSearchVideos(playVideo);
window.filterByTag = (tagId, tagName) => filterByTag(tagId, tagName, playVideo);
window.clearFilter = () => clearFilter(playVideo);
window.playVideo = playVideo;
window.closeVideoModal = closeVideoModal;
window.openAdvancedFilter = openAdvancedFilter;
window.closeAdvancedFilter = closeAdvancedFilter;
window.clearFilterSelection = clearFilterSelection;
window.applyAdvancedFilter = () => applyAdvancedFilter(playVideo);
window.shuffleVideos = () => shuffleVideos(playVideo);
window.goToAdvancedFilterPage = (page) => goToAdvancedFilterPage(page, playVideo);
window.openClockWallpaper = openClockWallpaper;
window.openMultiPlay = openMultiPlay;
window.openRandomRecommend = openRandomRecommend;
window.openVideoImport = openVideoImport;
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
