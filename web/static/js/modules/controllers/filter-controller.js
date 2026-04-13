import { appState } from '../stores/state.js';
import { videoService } from '../services/video.js';
import { showToast } from '../components/toast.js';
import { highlightActiveTag, clearActiveTags } from '../ui/tag-tree.js';
import {
    renderFilterTags,
    clearFilterSelectionUI,
    renderCurrentFilter
} from '../ui/filter-tags.js';
import { showLoading, showError as showVideoError, renderVideos } from '../ui/video-grid.js';
import { renderPagination } from '../ui/pagination.js';
import { closeMobileSidebar } from '../ui/mobile.js';
import { throttle, withLoading } from '../utils/debounce.js';

async function loadVideosByTagsAdvanced(tagsByCategory, shuffle, onVideoClick) {
    showLoading('videoGrid');

    try {
        const data = await videoService.loadVideosByTagsAdvanced(tagsByCategory, shuffle);
        renderVideos(data.videos, 'videoGrid', { onVideoClick });
        renderPagination(data, 'pagination', { onPageChange: (page) => {
            appState.set('currentPage', page);
            loadVideosByTagsAdvanced(appState.get('selectedFilterTagsByCategory'), false, onVideoClick);
        }});
    } catch (error) {
        showVideoError('videoGrid');
    }
}

async function loadVideosByTagIds(page, onVideoClick) {
    appState.set('currentPage', page);
    showLoading('videoGrid');

    try {
        const data = await videoService.loadVideos(page);
        renderVideos(data.videos, 'videoGrid', { onVideoClick });
        renderPagination(data, 'pagination', { onPageChange: (p) => loadVideosByTagIds(p, onVideoClick) });
    } catch (error) {
        showVideoError('videoGrid');
    }
}

export const filterByTag = throttle(function (tagId, tagName, onVideoClick) {
    highlightActiveTag(tagId);

    appState.set('currentTagIds', [tagId]);
    appState.set('selectedFilterTagsByCategory', {});
    appState.set('isRandomOrder', false);
    appState.set('randomSeed', Date.now());

    const filterContainer = document.getElementById('currentFilter');
    filterContainer.style.display = 'flex';
    document.getElementById('filterTags').innerHTML = `
        <span class="filter-tag">${tagName}</span>
    `;

    closeMobileSidebar();
    loadVideosByTagIds(1, onVideoClick);
}, 500);

export function clearFilter(onVideoClick) {
    appState.set('currentTagIds', []);
    appState.set('selectedFilterTags', []);
    appState.set('selectedFilterTagsByCategory', {});
    appState.set('randomSeed', Date.now());
    appState.set('isRandomOrder', false);

    clearActiveTags();

    document.getElementById('currentFilter').style.display = 'none';
    document.getElementById('clockWallpaperBtn').disabled = true;
    document.getElementById('multiPlayBtn').disabled = true;
    document.getElementById('randomRecommendBtn').disabled = true;
    document.getElementById('shuffleBtn').disabled = true;
    loadVideosByTagIds(1, onVideoClick);
}

export function openAdvancedFilter() {
    const modal = document.getElementById('advancedFilterModal');
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    renderFilterTags(appState.get('allTags'));
}

export function closeAdvancedFilter() {
    const modal = document.getElementById('advancedFilterModal');
    modal.classList.remove('show');
    document.body.style.overflow = '';
}

export function clearFilterSelection() {
    clearFilterSelectionUI();
}

export const applyAdvancedFilter = withLoading(async function (onVideoClick) {
    const filterTags = appState.get('selectedFilterTags');
    const filterTagsByCategory = appState.get('selectedFilterTagsByCategory');
    const tags = appState.get('allTags');

    if (filterTags.length === 0) {
        showToast('请至少选择一个标签');
        return;
    }

    closeAdvancedFilter();

    appState.set('currentTagIds', [...filterTags]);
    appState.set('currentPage', 1);
    appState.set('isRandomOrder', false);
    appState.set('randomSeed', Date.now());

    const filterContainer = document.getElementById('currentFilter');
    renderCurrentFilter(filterTagsByCategory, tags);
    filterContainer.style.display = 'flex';

    document.getElementById('clockWallpaperBtn').disabled = false;
    document.getElementById('multiPlayBtn').disabled = false;
    document.getElementById('randomRecommendBtn').disabled = false;
    document.getElementById('shuffleBtn').disabled = false;

    await loadVideosByTagsAdvanced(filterTagsByCategory, false, onVideoClick);

    document.dispatchEvent(new CustomEvent('advanced-filter-applied'));
}, null);

export const shuffleVideos = withLoading(async function (onVideoClick) {
    const filterTagsByCategory = appState.get('selectedFilterTagsByCategory');

    if (Object.keys(filterTagsByCategory).length === 0) {
        return;
    }

    appState.set('randomSeed', Date.now());
    appState.set('isRandomOrder', true);
    appState.set('currentPage', 1);

    const shuffleBtn = document.getElementById('shuffleBtn');
    shuffleBtn.classList.add('shuffling');

    await loadVideosByTagsAdvanced(filterTagsByCategory, true, onVideoClick);

    setTimeout(() => {
        shuffleBtn.classList.remove('shuffling');
    }, 300);
}, 'shuffleBtn');

export function goToAdvancedFilterPage(page, onVideoClick) {
    appState.set('currentPage', page);
    loadVideosByTagsAdvanced(appState.get('selectedFilterTagsByCategory'), false, onVideoClick);
}

export function openClockWallpaper() {
    if (Object.keys(appState.get('selectedFilterTagsByCategory')).length === 0) {
        showToast('请先进行多级筛选');
        return;
    }

    const params = encodeURIComponent(JSON.stringify(appState.get('selectedFilterTagsByCategory')));
    window.location.href = `/clock-wallpaper?filter=${params}`;
}

export function openMultiPlay() {
    if (Object.keys(appState.get('selectedFilterTagsByCategory')).length === 0) {
        showToast('请先进行多级筛选');
        return;
    }

    const params = encodeURIComponent(JSON.stringify(appState.get('selectedFilterTagsByCategory')));
    window.location.href = `/multi-play?filter=${params}`;
}

export function openRandomRecommend() {
    if (Object.keys(appState.get('selectedFilterTagsByCategory')).length === 0) {
        showToast('请先进行多级筛选');
        return;
    }

    const params = encodeURIComponent(JSON.stringify(appState.get('selectedFilterTagsByCategory')));
    window.location.href = `/random-recommend?filter=${params}`;
}

export function openVideoImport() {
    window.location.href = '/video-import';
}

export function logout() {
    window.location.href = '/logout';
}
