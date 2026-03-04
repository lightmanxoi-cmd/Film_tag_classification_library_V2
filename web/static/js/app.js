let currentPage = 1;
let currentTagIds = [];
let allTags = [];
let videoPlayer = null;
let currentVideoPath = '';
let touchStartX = 0;
let touchStartY = 0;

async function fetchWithAuth(url, options = {}) {
    const response = await fetch(url, options);
    if (response.status === 401) {
        const data = await response.clone().json().catch(() => ({}));
        if (data.timeout) {
            alert('登录已过期，请重新登录');
        }
        window.location.href = '/login';
        throw new Error('Unauthorized');
    }
    return response;
}

document.addEventListener('DOMContentLoaded', function() {
    loadTagTree();
    loadVideos();
    loadStats();
    
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
    
    initTouchGestures();
    
    initSwipeToClose();
});

function initTouchGestures() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobileOverlay');
    
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
    }, { passive: true });
    
    document.addEventListener('touchend', function(e) {
        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        const diffX = touchEndX - touchStartX;
        const diffY = touchEndY - touchStartY;
        
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
            const sidebar = document.getElementById('sidebar');
            const isOpen = sidebar.classList.contains('open');
            
            if (diffX > 0 && !isOpen && touchStartX < 30) {
                openMobileSidebar();
            } else if (diffX < 0 && isOpen) {
                closeMobileSidebar();
            }
        }
    }, { passive: true });
}

function initSwipeToClose() {
    const modals = document.querySelectorAll('.video-player-modal, .advanced-filter-modal');
    
    modals.forEach(modal => {
        let modalTouchStartY = 0;
        
        modal.addEventListener('touchstart', function(e) {
            modalTouchStartY = e.touches[0].clientY;
        }, { passive: true });
        
        modal.addEventListener('touchend', function(e) {
            const touchEndY = e.changedTouches[0].clientY;
            const diffY = touchEndY - modalTouchStartY;
            
            if (diffY > 100) {
                if (modal.id === 'videoModal') {
                    closeVideoModal();
                } else if (modal.id === 'advancedFilterModal') {
                    closeAdvancedFilter();
                }
            }
        }, { passive: true });
    });
}

function toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar.classList.contains('open')) {
        closeMobileSidebar();
    } else {
        openMobileSidebar();
    }
}

function openMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobileOverlay');
    sidebar.classList.add('open');
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobileOverlay');
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
}

function toggleMobileSearch() {
    const searchBar = document.getElementById('mobileSearchBar');
    if (searchBar.classList.contains('show')) {
        closeMobileSearch();
    } else {
        searchBar.classList.add('show');
        document.getElementById('mobileSearchInput').focus();
    }
}

function closeMobileSearch() {
    const searchBar = document.getElementById('mobileSearchBar');
    searchBar.classList.remove('show');
    document.getElementById('mobileSearchInput').value = '';
}

function mobileSearchVideos() {
    const keyword = document.getElementById('mobileSearchInput').value.trim();
    
    if (!keyword) {
        loadVideos(1);
        closeMobileSearch();
        return;
    }
    
    currentTagIds = [];
    document.getElementById('currentFilter').style.display = 'none';
    
    const container = document.getElementById('videoGrid');
    container.innerHTML = '<div class="loading">搜索中...</div>';
    
    fetchWithAuth(`/api/videos?page=1&page_size=50&search=${encodeURIComponent(keyword)}`)
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                renderVideos(result.data.videos);
                renderPagination(result.data);
                
                document.getElementById('currentFilter').style.display = 'flex';
                document.getElementById('filterTags').innerHTML = `
                    <span class="filter-tag">搜索: "${keyword}"</span>
                `;
            }
            closeMobileSearch();
        })
        .catch(error => {
            console.error('搜索失败:', error);
            container.innerHTML = '<div class="loading">搜索失败</div>';
            closeMobileSearch();
        });
}

async function loadTagTree() {
    try {
        const response = await fetchWithAuth('/api/tags/tree');
        const result = await response.json();
        
        if (result.success) {
            allTags = result.data;
            renderTagTree(result.data);
        }
    } catch (error) {
        console.error('加载标签树失败:', error);
        document.getElementById('tagTree').innerHTML = '<div class="loading">加载失败</div>';
    }
}

function renderTagTree(tags) {
    const container = document.getElementById('tagTree');
    container.innerHTML = '';
    
    tags.forEach(tag => {
        const category = document.createElement('div');
        category.className = 'tag-category';
        
        const parent = document.createElement('div');
        parent.className = 'tag-parent';
        parent.innerHTML = `
            <span class="expand-icon">▶</span>
            <span class="tag-name">${tag.name}</span>
        `;
        
        const children = document.createElement('div');
        children.className = 'tag-children';
        
        if (tag.children && tag.children.length > 0) {
            tag.children.forEach(child => {
                const childEl = document.createElement('div');
                childEl.className = 'tag-child';
                childEl.dataset.tagId = child.id;
                childEl.innerHTML = `
                    <span>${child.name}</span>
                    <span class="video-count">${child.video_count || 0}</span>
                `;
                childEl.addEventListener('click', (e) => {
                    e.stopPropagation();
                    filterByTag(child.id, child.name);
                });
                children.appendChild(childEl);
            });
        }
        
        parent.addEventListener('click', () => {
            parent.classList.toggle('expanded');
            children.classList.toggle('show');
        });
        
        category.appendChild(parent);
        category.appendChild(children);
        container.appendChild(category);
    });
}

async function loadVideos(page = 1) {
    currentPage = page;
    const container = document.getElementById('videoGrid');
    container.innerHTML = '<div class="loading">加载中...</div>';
    
    try {
        let result;
        
        if (currentTagIds.length > 0) {
            const response = await fetchWithAuth('/api/videos/by-tags', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tag_ids: currentTagIds,
                    page: page,
                    page_size: 50,
                    match_all: false
                })
            });
            result = await response.json();
        } else {
            const response = await fetchWithAuth(`/api/videos?page=${page}&page_size=50`);
            result = await response.json();
        }
        
        if (result.success) {
            renderVideos(result.data.videos);
            renderPagination(result.data);
        }
    } catch (error) {
        console.error('加载视频失败:', error);
        container.innerHTML = '<div class="loading">加载失败</div>';
    }
}

function renderVideos(videos) {
    const container = document.getElementById('videoGrid');
    
    if (videos.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>没有找到视频</h3>
                <p>请尝试其他筛选条件</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '';
    
    videos.forEach(video => {
        const card = document.createElement('div');
        card.className = 'video-card';
        card.dataset.videoId = video.id;
        
        const ext = video.file_path.split('.').pop().toLowerCase();
        const formatClass = ['mkv', 'wmv', 'avi'].includes(ext) ? 'non-native' : '';
        
        const tagsHtml = video.tags.slice(0, 3).map(t => 
            `<span class="video-tag">${t.name}</span>`
        ).join('');
        
        const thumbnailStyle = video.thumbnail ? 
            `style="background-image: url('${video.thumbnail}'); background-size: cover; background-position: center;"` : '';
        
        card.innerHTML = `
            <div class="thumbnail ${formatClass}" ${thumbnailStyle}>
                ${!video.thumbnail ? '<span class="play-icon">▶</span>' : '<span class="play-overlay">▶</span>'}
                <span class="format-badge">${ext.toUpperCase()}</span>
            </div>
            <div class="video-overlay">
                <div class="video-title">${video.title}</div>
                <div class="video-tags">${tagsHtml}</div>
            </div>
        `;
        
        card.addEventListener('click', () => playVideo(video.id, video.title, video.tags, video.file_path));
        container.appendChild(card);
    });
}

function renderPagination(data) {
    const container = document.getElementById('pagination');
    
    if (data.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = `
        <button onclick="loadVideos(${data.page - 1})" ${data.page <= 1 ? 'disabled' : ''}>
            上一页
        </button>
        <span class="page-info">第 ${data.page} / ${data.total_pages} 页 (共 ${data.total} 部)</span>
        <button onclick="loadVideos(${data.page + 1})" ${data.page >= data.total_pages ? 'disabled' : ''}>
            下一页
        </button>
    `;
    
    container.innerHTML = html;
}

function filterByTag(tagId, tagName) {
    document.querySelectorAll('.tag-child').forEach(el => {
        el.classList.remove('active');
        if (parseInt(el.dataset.tagId) === tagId) {
            el.classList.add('active');
        }
    });
    
    currentTagIds = [tagId];
    
    const filterContainer = document.getElementById('currentFilter');
    filterContainer.style.display = 'flex';
    document.getElementById('filterTags').innerHTML = `
        <span class="filter-tag">${tagName}</span>
    `;
    
    closeMobileSidebar();
    loadVideos(1);
}

function clearFilter() {
    currentTagIds = [];
    selectedFilterTags = [];
    
    document.querySelectorAll('.tag-child').forEach(el => {
        el.classList.remove('active');
    });
    
    document.getElementById('currentFilter').style.display = 'none';
    loadVideos(1);
}

async function searchVideos() {
    const keyword = document.getElementById('searchInput').value.trim();
    
    if (!keyword) {
        loadVideos(1);
        return;
    }
    
    currentTagIds = [];
    document.getElementById('currentFilter').style.display = 'none';
    
    const container = document.getElementById('videoGrid');
    container.innerHTML = '<div class="loading">搜索中...</div>';
    
    try {
        const response = await fetchWithAuth(`/api/videos?page=1&page_size=50&search=${encodeURIComponent(keyword)}`);
        const result = await response.json();
        
        if (result.success) {
            renderVideos(result.data.videos);
            renderPagination(result.data);
            
            document.getElementById('currentFilter').style.display = 'flex';
            document.getElementById('filterTags').innerHTML = `
                <span class="filter-tag">搜索: "${keyword}"</span>
            `;
        }
    } catch (error) {
        console.error('搜索失败:', error);
        container.innerHTML = '<div class="loading">搜索失败</div>';
    }
}

async function playVideo(videoId, title, tags, filePath) {
    try {
        currentVideoPath = filePath;
        
        const response = await fetchWithAuth(`/api/video/stream/${videoId}`);
        const result = await response.json();
        
        if (result.success) {
            const modal = document.getElementById('videoModal');
            const formatNotice = document.getElementById('formatNotice');
            
            document.getElementById('modalTitle').textContent = result.data.title;
            
            const tagsContainer = document.getElementById('modalTags');
            tagsContainer.innerHTML = tags.map(t => 
                `<span class="video-tag">${t.name}</span>`
            ).join('');
            
            const fileExt = result.data.file_ext || '.mp4';
            const nonNativeFormats = ['.mkv', '.wmv', '.avi'];
            
            if (nonNativeFormats.includes(fileExt)) {
                formatNotice.style.display = 'block';
            } else {
                formatNotice.style.display = 'none';
            }
            
            const playerContainer = document.querySelector('.modal-content');
            let videoElement = document.getElementById('videoPlayer');
            
            if (videoPlayer) {
                try {
                    videoPlayer.dispose();
                } catch (e) {
                    console.log('Dispose error:', e);
                }
                videoPlayer = null;
            }
            
            if (!videoElement || !document.body.contains(videoElement)) {
                videoElement = document.createElement('video');
                videoElement.id = 'videoPlayer';
                videoElement.className = 'video-js vjs-big-play-centered vjs-fluid';
                videoElement.controls = true;
                videoElement.preload = 'auto';
                videoElement.setAttribute('playsinline', '');
                videoElement.setAttribute('webkit-playsinline', '');
                
                const playerActions = document.querySelector('.player-actions');
                playerContainer.insertBefore(videoElement, playerActions);
            }
            
            videoPlayer = videojs('videoPlayer', {
                fluid: true,
                responsive: true,
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
                }
            });
            
            videoPlayer.src({
                src: result.data.stream_url,
                type: getMimeType(fileExt)
            });
            
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
            
            videoPlayer.ready(function() {
                this.play().catch(function(error) {
                    console.log('自动播放失败，请手动点击播放:', error);
                });
            });
        }
    } catch (error) {
        console.error('获取视频信息失败:', error);
        alert('无法播放视频: ' + error.message);
    }
}

function getMimeType(ext) {
    const mimeTypes = {
        '.mp4': 'video/mp4',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
        '.avi': 'video/x-msvideo',
        '.wmv': 'video/x-ms-wmv',
        '.mov': 'video/quicktime'
    };
    return mimeTypes[ext] || 'video/mp4';
}

function openLocalFile() {
    if (currentVideoPath) {
        window.location.href = 'file:///' + currentVideoPath.replace(/\\/g, '/');
    }
}

function copyFilePath() {
    if (currentVideoPath) {
        navigator.clipboard.writeText(currentVideoPath).then(() => {
            showToast('路径已复制: ' + currentVideoPath);
        }).catch(err => {
            console.error('复制失败:', err);
            prompt('请手动复制路径:', currentVideoPath);
        });
    }
}

function showToast(message) {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.style.cssText = `
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(229, 9, 20, 0.9);
            color: #fff;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            z-index: 3000;
            opacity: 0;
            transition: opacity 0.3s;
            max-width: 90%;
            text-align: center;
        `;
        document.body.appendChild(toast);
    }
    
    toast.textContent = message;
    toast.style.opacity = '1';
    
    setTimeout(() => {
        toast.style.opacity = '0';
    }, 3000);
}

function closeVideoModal() {
    const modal = document.getElementById('videoModal');
    
    if (videoPlayer) {
        videoPlayer.pause();
        videoPlayer.dispose();
        videoPlayer = null;
    }
    
    modal.classList.remove('show');
    document.body.style.overflow = '';
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeVideoModal();
        closeAdvancedFilter();
        closeMobileSidebar();
        closeMobileSearch();
    }
});

async function loadStats() {
    try {
        const response = await fetchWithAuth('/api/stats');
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('videoCount').textContent = result.data.video_count;
        }
    } catch (error) {
        console.error('加载统计信息失败:', error);
    }
}

let selectedFilterTags = [];
let selectedFilterTagsByCategory = {};

function openAdvancedFilter() {
    const modal = document.getElementById('advancedFilterModal');
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    renderFilterTags();
}

function closeAdvancedFilter() {
    const modal = document.getElementById('advancedFilterModal');
    modal.classList.remove('show');
    document.body.style.overflow = '';
}

function renderFilterTags() {
    const container = document.getElementById('filterTagsContainer');
    
    if (!allTags || allTags.length === 0) {
        container.innerHTML = '<div class="loading">请等待标签加载...</div>';
        return;
    }
    
    container.innerHTML = '';
    
    allTags.forEach(category => {
        const categoryDiv = document.createElement('div');
        categoryDiv.className = 'filter-category';
        
        const selectedInCategory = selectedFilterTagsByCategory[category.id] || [];
        
        categoryDiv.innerHTML = `
            <div class="filter-category-header" onclick="toggleFilterCategory(this)">
                <span class="toggle-icon">▼</span>
                <h4>${category.name}</h4>
            </div>
            <div class="filter-category-tags">
                ${category.children.map(tag => `
                    <label class="filter-tag-item ${selectedFilterTags.includes(tag.id) ? 'selected' : ''}" data-tag-id="${tag.id}" data-category-id="${category.id}">
                        <input type="checkbox" 
                               ${selectedFilterTags.includes(tag.id) ? 'checked' : ''} 
                               onchange="toggleFilterTag(${tag.id}, ${category.id}, '${tag.name.replace(/'/g, "\\'")}')">
                        <span>${tag.name}</span>
                        <span class="tag-count">${tag.video_count || 0}</span>
                    </label>
                `).join('')}
            </div>
        `;
        
        container.appendChild(categoryDiv);
    });
}

function toggleFilterCategory(header) {
    const category = header.parentElement;
    category.classList.toggle('collapsed');
}

function toggleFilterTag(tagId, categoryId, tagName) {
    const index = selectedFilterTags.indexOf(tagId);
    
    if (index === -1) {
        selectedFilterTags.push(tagId);
        if (!selectedFilterTagsByCategory[categoryId]) {
            selectedFilterTagsByCategory[categoryId] = [];
        }
        selectedFilterTagsByCategory[categoryId].push(tagId);
    } else {
        selectedFilterTags.splice(index, 1);
        if (selectedFilterTagsByCategory[categoryId]) {
            const catIndex = selectedFilterTagsByCategory[categoryId].indexOf(tagId);
            if (catIndex !== -1) {
                selectedFilterTagsByCategory[categoryId].splice(catIndex, 1);
            }
        }
    }
    
    const tagItem = document.querySelector(`.filter-tag-item[data-tag-id="${tagId}"]`);
    if (tagItem) {
        tagItem.classList.toggle('selected');
    }
    
    updateSelectedTagsList();
}

function updateSelectedTagsList() {
    const container = document.getElementById('selectedTagsList');
    
    if (selectedFilterTags.length === 0) {
        container.innerHTML = '<span class="no-selection">未选择任何标签</span>';
        return;
    }
    
    const selectedTagsInfo = [];
    allTags.forEach(category => {
        category.children.forEach(tag => {
            if (selectedFilterTags.includes(tag.id)) {
                selectedTagsInfo.push({ id: tag.id, name: tag.name, categoryId: category.id });
            }
        });
    });
    
    container.innerHTML = selectedTagsInfo.map(tag => `
        <span class="selected-tag-chip">
            ${tag.name}
            <span class="remove-tag" onclick="removeFilterTag(${tag.id}, ${tag.categoryId})">×</span>
        </span>
    `).join('');
}

function removeFilterTag(tagId, categoryId) {
    const index = selectedFilterTags.indexOf(tagId);
    if (index !== -1) {
        selectedFilterTags.splice(index, 1);
    }
    
    if (selectedFilterTagsByCategory[categoryId]) {
        const catIndex = selectedFilterTagsByCategory[categoryId].indexOf(tagId);
        if (catIndex !== -1) {
            selectedFilterTagsByCategory[categoryId].splice(catIndex, 1);
        }
    }
    
    const tagItem = document.querySelector(`.filter-tag-item[data-tag-id="${tagId}"]`);
    if (tagItem) {
        tagItem.classList.remove('selected');
        tagItem.querySelector('input').checked = false;
    }
    
    updateSelectedTagsList();
}

function clearFilterSelection() {
    selectedFilterTags = [];
    selectedFilterTagsByCategory = {};
    
    document.querySelectorAll('.filter-tag-item.selected').forEach(item => {
        item.classList.remove('selected');
        item.querySelector('input').checked = false;
    });
    
    updateSelectedTagsList();
}

async function applyAdvancedFilter() {
    if (selectedFilterTags.length === 0) {
        showToast('请至少选择一个标签');
        return;
    }
    
    closeAdvancedFilter();
    
    currentTagIds = [...selectedFilterTags];
    currentPage = 1;
    
    const filterContainer = document.getElementById('currentFilter');
    const filterTagsSpan = document.getElementById('filterTags');
    
    const categoryGroups = [];
    allTags.forEach(category => {
        const selectedInCategory = (selectedFilterTagsByCategory[category.id] || []);
        if (selectedInCategory.length > 0) {
            const tagNames = category.children
                .filter(tag => selectedInCategory.includes(tag.id))
                .map(tag => tag.name);
            categoryGroups.push({
                categoryName: category.name,
                tagNames: tagNames
            });
        }
    });
    
    let filterHtml = '';
    categoryGroups.forEach((group, index) => {
        if (index > 0) {
            filterHtml += '<span class="filter-separator">+</span>';
        }
        group.tagNames.forEach((name, tagIndex) => {
            if (tagIndex > 0) {
                filterHtml += '<span class="filter-separator or">或</span>';
            }
            filterHtml += `<span class="filter-tag">${name}</span>`;
        });
    });
    
    filterTagsSpan.innerHTML = filterHtml;
    filterContainer.style.display = 'flex';
    
    await loadVideosByTagsAdvanced(selectedFilterTagsByCategory);
}

async function loadVideosByTagsAdvanced(tagsByCategory) {
    const container = document.getElementById('videoGrid');
    container.innerHTML = '<div class="loading">加载中...</div>';
    
    try {
        const response = await fetchWithAuth('/api/videos/by-tags-advanced', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tags_by_category: tagsByCategory,
                page: currentPage,
                page_size: 50
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            renderVideos(result.data.videos);
            renderPagination(result.data);
        }
    } catch (error) {
        console.error('加载视频失败:', error);
        container.innerHTML = '<div class="loading">加载失败</div>';
    }
}

let lastScrollTop = 0;
const navbar = document.querySelector('.navbar');

window.addEventListener('scroll', function() {
    if (window.innerWidth <= 768) {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        if (scrollTop > lastScrollTop && scrollTop > 100) {
            navbar.style.transform = 'translateY(-100%)';
        } else {
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
    }
}, { passive: true });

window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
        closeMobileSidebar();
        closeMobileSearch();
        navbar.style.transform = 'translateY(0)';
    }
});
