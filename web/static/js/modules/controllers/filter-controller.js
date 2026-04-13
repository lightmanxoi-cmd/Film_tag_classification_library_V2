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

async function loadVideosByTagsAdvanced(tagsByCategory, shuffle = false, onVideoClick) {
    showLoading('videoGrid');

    try {
        const data = await videoService.loadVideosByTagsAdvanced(tagsByCategory, shuffle);
        renderVideos(data.videos, 'videoGrid', { onVideoClick });
        renderPagination(data, 'pagination', { onPageChange: (page) => {
            setCurrentPage(page);
            loadVideosByTagsAdvanced(getSelectedFilterTagsByCategory(), false, onVideoClick);
        }});
    } catch (error) {
        showVideoError('videoGrid');
    }
}

export function filterByTag(tagId, tagName, onVideoClick) {
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
    loadVideosByTagIds(1, onVideoClick);
}

async function loadVideosByTagIds(page, onVideoClick) {
    setCurrentPage(page);
    showLoading('videoGrid');

    try {
        const data = await videoService.loadVideos(page);
        renderVideos(data.videos, 'videoGrid', { onVideoClick });
        renderPagination(data, 'pagination', { onPageChange: (p) => loadVideosByTagIds(p, onVideoClick) });
    } catch (error) {
        showVideoError('videoGrid');
    }
}

export function clearFilter(onVideoClick) {
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
    loadVideosByTagIds(1, onVideoClick);
}

export function openAdvancedFilter() {
    const modal = document.getElementById('advancedFilterModal');
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    renderFilterTags(getAllTags());
}

export function closeAdvancedFilter() {
    const modal = document.getElementById('advancedFilterModal');
    modal.classList.remove('show');
    document.body.style.overflow = '';
}

export function clearFilterSelection() {
    clearFilterSelectionUI();
}

export async function applyAdvancedFilter(onVideoClick) {
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

    await loadVideosByTagsAdvanced(filterTagsByCategory, false, onVideoClick);

    document.dispatchEvent(new CustomEvent('advanced-filter-applied'));
}

export async function shuffleVideos(onVideoClick) {
    const filterTagsByCategory = getSelectedFilterTagsByCategory();

    if (Object.keys(filterTagsByCategory).length === 0) {
        return;
    }

    const shuffleBtn = document.getElementById('shuffleBtn');
    shuffleBtn.classList.add('shuffling');

    setRandomSeed(Date.now());
    setIsRandomOrder(true);
    setCurrentPage(1);

    await loadVideosByTagsAdvanced(filterTagsByCategory, true, onVideoClick);

    setTimeout(() => {
        shuffleBtn.classList.remove('shuffling');
    }, 300);
}

export function goToAdvancedFilterPage(page, onVideoClick) {
    setCurrentPage(page);
    loadVideosByTagsAdvanced(getSelectedFilterTagsByCategory(), false, onVideoClick);
}

export function openClockWallpaper() {
    if (Object.keys(getSelectedFilterTagsByCategory()).length === 0) {
        showToast('请先进行多级筛选');
        return;
    }

    const params = encodeURIComponent(JSON.stringify(getSelectedFilterTagsByCategory()));
    window.location.href = `/clock-wallpaper?filter=${params}`;
}

export function openMultiPlay() {
    if (Object.keys(getSelectedFilterTagsByCategory()).length === 0) {
        showToast('请先进行多级筛选');
        return;
    }

    const params = encodeURIComponent(JSON.stringify(getSelectedFilterTagsByCategory()));
    window.location.href = `/multi-play?filter=${params}`;
}

export function openRandomRecommend() {
    if (Object.keys(getSelectedFilterTagsByCategory()).length === 0) {
        showToast('请先进行多级筛选');
        return;
    }

    const params = encodeURIComponent(JSON.stringify(getSelectedFilterTagsByCategory()));
    window.location.href = `/random-recommend?filter=${params}`;
}

export function openVideoImport() {
    window.location.href = '/video-import';
}

export function logout() {
    window.location.href = '/logout';
}
