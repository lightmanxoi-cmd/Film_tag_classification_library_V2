import { appState } from '../stores/state.js';
import { videoService } from '../services/video.js';
import { showLoading, showError as showVideoError, renderVideos } from '../ui/video-grid.js';
import { renderPagination } from '../ui/pagination.js';
import { closeMobileSearch } from '../ui/mobile.js';

function setCurrentTagIds(ids) {
    appState.set('currentTagIds', ids);
}

export async function searchVideos(onVideoClick) {
    const keyword = document.getElementById('searchInput').value.trim();

    if (!keyword) {
        loadVideos(1, onVideoClick);
        return;
    }

    setCurrentTagIds([]);
    document.getElementById('currentFilter').style.display = 'none';
    showLoading('videoGrid', '搜索中...');

    try {
        const data = await videoService.searchVideos(keyword);
        renderVideos(data.videos, 'videoGrid', { onVideoClick });
        renderPagination(data, 'pagination', { onPageChange: (page) => loadVideos(page, onVideoClick) });

        document.getElementById('currentFilter').style.display = 'flex';
        document.getElementById('filterTags').innerHTML = `
            <span class="filter-tag">搜索: "${keyword}"</span>
        `;
    } catch (error) {
        showVideoError('videoGrid', '搜索失败');
    }
}

export async function mobileSearchVideos(onVideoClick) {
    const keyword = document.getElementById('mobileSearchInput').value.trim();

    if (!keyword) {
        loadVideos(1, onVideoClick);
        closeMobileSearch();
        return;
    }

    setCurrentTagIds([]);
    document.getElementById('currentFilter').style.display = 'none';
    showLoading('videoGrid', '搜索中...');

    try {
        const data = await videoService.searchVideos(keyword);
        renderVideos(data.videos, 'videoGrid', { onVideoClick });
        renderPagination(data, 'pagination', { onPageChange: (page) => loadVideos(page, onVideoClick) });

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

async function loadVideos(page = 1, onVideoClick) {
    appState.set('currentPage', page);
    showLoading('videoGrid');

    try {
        const data = await videoService.loadVideos(page);
        renderVideos(data.videos, 'videoGrid', { onVideoClick });
        renderPagination(data, 'pagination', { onPageChange: (p) => loadVideos(p, onVideoClick) });
    } catch (error) {
        showVideoError('videoGrid');
    }
}
