/**
 * 视频标签管理系统 - 主应用脚本
 * 
 * 本文件是视频标签管理系统的前端核心脚本，负责：
 * - 视频列表的加载、搜索和筛选
 * - 标签树的渲染和交互
 * - 视频播放器的初始化和控制
 * - 移动端适配和触摸手势
 * - 高级筛选功能
 * 
 * 主要功能模块：
 * 1. 数据获取模块：fetchWithAuth、loadTagTree、loadVideos
 * 2. 渲染模块：renderTagTree、renderVideos、renderPagination
 * 3. 筛选模块：filterByTag、openAdvancedFilter、applyAdvancedFilter
 * 4. 播放器模块：playVideo、closeVideoModal
 * 5. 移动端模块：initTouchGestures、toggleMobileSidebar
 * 
 * 作者：Video Library System
 * 创建时间：2024
 */

/* ==================== 全局变量定义 ==================== */

/** 当前页码 */
let currentPage = 1;

/** 当前选中的标签ID列表 */
let currentTagIds = [];

/** 所有标签数据（用于高级筛选） */
let allTags = [];

/** Video.js 播放器实例 */
let videoPlayer = null;

/** 当前播放视频的文件路径 */
let currentVideoPath = '';

/** 触摸开始时的X坐标（用于滑动手势） */
let touchStartX = 0;

/** 触摸开始时的Y坐标（用于滑动手势） */
let touchStartY = 0;

/** 随机种子（用于随机排序） */
let randomSeed = Date.now();

/** 当前是否处于随机排序模式 */
let isRandomOrder = false;

/** 高级筛选选中的标签ID列表 */
let selectedFilterTags = [];

/** 高级筛选按分类分组的标签 {categoryId: [tagId, ...]} */
let selectedFilterTagsByCategory = {};

/* ==================== 认证与请求模块 ==================== */

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
            alert('登录已过期，请重新登录');
        }
        window.location.href = '/login';
        throw new Error('Unauthorized');
    }
    return response;
}

/* ==================== 初始化模块 ==================== */

/**
 * DOM 加载完成后初始化
 * 
 * 页面加载完成后执行以下初始化操作：
 * 1. 加载标签树
 * 2. 加载视频列表
 * 3. 加载统计信息
 * 4. 绑定搜索框回车事件
 * 5. 初始化触摸手势
 * 6. 初始化滑动关闭功能
 */
document.addEventListener('DOMContentLoaded', function() {
    loadTagTree();
    loadVideos();
    loadStats();
    initSessionTimeout();
    
    // 绑定桌面端搜索框回车事件
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchVideos();
        }
    });
    
    // 绑定移动端搜索框回车事件
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

/* ==================== 触摸手势模块 ==================== */

/**
 * 初始化触摸手势
 * 
 * 为移动端添加侧边栏滑动手势支持：
 * - 从屏幕左边缘向右滑动：打开侧边栏
 * - 在侧边栏打开时向左滑动：关闭侧边栏
 */
function initTouchGestures() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobileOverlay');
    
    // 记录触摸起始位置
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
    }, { passive: true });
    
    // 处理触摸结束，判断滑动方向
    document.addEventListener('touchend', function(e) {
        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        const diffX = touchEndX - touchStartX;
        const diffY = touchEndY - touchStartY;
        
        // 判断是否为水平滑动（水平距离大于垂直距离，且超过50px）
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
            const sidebar = document.getElementById('sidebar');
            const isOpen = sidebar.classList.contains('open');
            
            // 从左边缘向右滑动打开侧边栏
            if (diffX > 0 && !isOpen && touchStartX < 30) {
                openMobileSidebar();
            } else if (diffX < 0 && isOpen) {
                // 向左滑动关闭侧边栏
                closeMobileSidebar();
            }
        }
    }, { passive: true });
}

/**
 * 初始化滑动关闭功能
 * 
 * 为模态框添加向下滑动关闭的手势支持。
 * 用户可以在模态框顶部向下滑动来关闭模态框。
 */
function initSwipeToClose() {
    const modals = document.querySelectorAll('.video-player-modal, .advanced-filter-modal');
    
    modals.forEach(modal => {
        let modalTouchStartY = 0;
        let modalTouchStartX = 0;
        let isScrolling = false;
        let touchStartTime = 0;
        let startScrollTop = 0;
        
        modal.addEventListener('touchstart', function(e) {
            modalTouchStartY = e.touches[0].clientY;
            modalTouchStartX = e.touches[0].clientX;
            isScrolling = false;
            touchStartTime = Date.now();
            
            // 记录滚动容器初始滚动位置
            const scrollableContent = modal.querySelector('.filter-modal-body');
            if (scrollableContent) {
                startScrollTop = scrollableContent.scrollTop;
            } else {
                startScrollTop = 0;
            }
        }, { passive: true });
        
        modal.addEventListener('touchmove', function(e) {
            const touchCurrentY = e.touches[0].clientY;
            const touchCurrentX = e.touches[0].clientX;
            const diffY = touchCurrentY - modalTouchStartY;
            const diffX = touchCurrentX - modalTouchStartX;
            
            // 判断是否为垂直滚动
            if (Math.abs(diffY) > Math.abs(diffX) && Math.abs(diffY) > 10) {
                isScrolling = true;
            }
        }, { passive: true });
        
        modal.addEventListener('touchend', function(e) {
            // 如果正在滚动内容，不触发关闭
            if (isScrolling) return;
            
            const touchEndY = e.changedTouches[0].clientY;
            const diffY = touchEndY - modalTouchStartY;
            const touchDuration = Date.now() - touchStartTime;
            
            const scrollableContent = modal.querySelector('.filter-modal-body');
            const currentScrollTop = scrollableContent ? scrollableContent.scrollTop : 0;
            
            // 向下滑动超过100px且快速滑动时关闭模态框
            if (diffY > 100 && touchDuration < 500 && currentScrollTop === 0 && startScrollTop === 0) {
                if (modal.id === 'videoModal') {
                    closeVideoModal();
                } else if (modal.id === 'advancedFilterModal') {
                    closeAdvancedFilter();
                }
            }
        }, { passive: true });
    });
}

/* ==================== 移动端侧边栏模块 ==================== */

/**
 * 切换移动端侧边栏显示状态
 */
function toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar.classList.contains('open')) {
        closeMobileSidebar();
    } else {
        openMobileSidebar();
    }
}

/**
 * 打开移动端侧边栏
 */
function openMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobileOverlay');
    sidebar.classList.add('open');
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

/**
 * 关闭移动端侧边栏
 */
function closeMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobileOverlay');
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
}

/* ==================== 移动端搜索模块 ==================== */

/**
 * 切换移动端搜索栏显示状态
 */
function toggleMobileSearch() {
    const searchBar = document.getElementById('mobileSearchBar');
    if (searchBar.classList.contains('show')) {
        closeMobileSearch();
    } else {
        searchBar.classList.add('show');
        document.getElementById('mobileSearchInput').focus();
    }
}

/**
 * 关闭移动端搜索栏
 */
function closeMobileSearch() {
    const searchBar = document.getElementById('mobileSearchBar');
    searchBar.classList.remove('show');
    document.getElementById('mobileSearchInput').value = '';
}

/**
 * 移动端搜索视频
 * 
 * 执行搜索并更新视频列表，搜索完成后关闭搜索栏。
 */
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

/* ==================== 标签树模块 ==================== */

/**
 * 加载标签树数据
 * 
 * 从服务器获取标签树结构并渲染到页面。
 */
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

/**
 * 渲染标签树
 * 
 * 将标签数据渲染为可折叠的树形结构。
 * 一级标签为可展开的分类，二级标签为可点击的筛选项。
 * 
 * @param {Array} tags - 标签树数据
 */
function renderTagTree(tags) {
    const container = document.getElementById('tagTree');
    container.innerHTML = '';
    
    tags.forEach(tag => {
        const category = document.createElement('div');
        category.className = 'tag-category';
        
        // 创建一级标签（父标签）
        const parent = document.createElement('div');
        parent.className = 'tag-parent';
        parent.innerHTML = `
            <span class="expand-icon">▶</span>
            <span class="tag-name">${tag.name}</span>
        `;
        
        // 创建二级标签容器
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
                // 点击二级标签进行筛选
                childEl.addEventListener('click', (e) => {
                    e.stopPropagation();
                    filterByTag(child.id, child.name);
                });
                children.appendChild(childEl);
            });
        }
        
        // 点击一级标签展开/收起
        parent.addEventListener('click', () => {
            parent.classList.toggle('expanded');
            children.classList.toggle('show');
        });
        
        category.appendChild(parent);
        category.appendChild(children);
        container.appendChild(category);
    });
}

/* ==================== 视频列表模块 ==================== */

/**
 * 加载视频列表
 * 
 * 根据当前筛选条件加载视频列表。
 * 如果有选中的标签，则按标签筛选；否则随机加载视频。
 * 
 * @param {number} page - 页码，默认为1
 */
async function loadVideos(page = 1) {
    currentPage = page;
    const container = document.getElementById('videoGrid');
    container.innerHTML = '<div class="loading">加载中...</div>';
    
    try {
        let result;
        
        if (currentTagIds.length > 0) {
            // 按标签筛选视频
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
            // 随机加载视频
            const response = await fetchWithAuth(`/api/videos?page=${page}&page_size=50&random=true&seed=${randomSeed}`);
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

/**
 * 渲染视频卡片列表
 * 
 * 将视频数据渲染为卡片网格布局。
 * 每个卡片包含缩略图、标题、标签等信息。
 * 
 * @param {Array} videos - 视频数据数组
 */
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
        
        // 获取文件扩展名并判断是否为原生支持格式
        const ext = video.file_path.split('.').pop().toLowerCase();
        const formatClass = ['mkv', 'wmv', 'avi'].includes(ext) ? 'non-native' : '';
        
        // 只显示二级标签（有父标签的标签）
        const childTags = video.tags.filter(t => t.parent_id);
        const tagsHtml = childTags.slice(0, 3).map(t => 
            `<span class="video-tag">${t.name}</span>`
        ).join('');
        
        // 设置缩略图样式
        const thumbnailStyle = video.thumbnail ? 
            `style="background-image: url('${video.thumbnail}'); background-size: cover; background-position: center;"` : '';
        
        // GIF 预览元素（鼠标悬停时显示）
        const gifElement = video.gif ? 
            `<img class="gif-preview" src="${video.gif}" alt="${video.title}" style="display: none;">` : '';
        
        card.innerHTML = `
            <div class="thumbnail ${formatClass}" ${thumbnailStyle}>
                ${!video.thumbnail ? '<span class="play-icon">▶</span>' : '<span class="play-overlay">▶</span>'}
                <span class="format-badge">${ext.toUpperCase()}</span>
                ${gifElement}
            </div>
            <div class="video-overlay">
                <div class="video-title">${video.title}</div>
                <div class="video-tags">${tagsHtml}</div>
            </div>
        `;
        
        // 如果有 GIF，添加鼠标悬停切换效果
        if (video.gif) {
            const thumbnailDiv = card.querySelector('.thumbnail');
            const gifImg = card.querySelector('.gif-preview');
            
            card.addEventListener('mouseenter', () => {
                thumbnailDiv.style.backgroundImage = 'none';
                gifImg.style.display = 'block';
            });
            
            card.addEventListener('mouseleave', () => {
                gifImg.style.display = 'none';
                if (video.thumbnail) {
                    thumbnailDiv.style.backgroundImage = `url('${video.thumbnail}')`;
                }
            });
        }
        
        // 点击卡片播放视频
        card.addEventListener('click', () => playVideo(video.id, video.title, video.tags, video.file_path));
        container.appendChild(card);
    });
}

/**
 * 渲染分页控件
 * 
 * 根据分页数据生成分页按钮。
 * 
 * @param {Object} data - 分页数据，包含 page、total_pages、total 等字段
 */
function renderPagination(data) {
    const container = document.getElementById('pagination');
    
    if (data.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    const prevOnClick = Object.keys(selectedFilterTagsByCategory).length > 0
        ? `goToAdvancedFilterPage(${data.page - 1})`
        : `loadVideos(${data.page - 1})`;
    const nextOnClick = Object.keys(selectedFilterTagsByCategory).length > 0
        ? `goToAdvancedFilterPage(${data.page + 1})`
        : `loadVideos(${data.page + 1})`;
    
    let html = `
        <button onclick="${prevOnClick}" ${data.page <= 1 ? 'disabled' : ''}>
            上一页
        </button>
        <span class="page-info">第 ${data.page} / ${data.total_pages} 页 (共 ${data.total} 部)</span>
        <button onclick="${nextOnClick}" ${data.page >= data.total_pages ? 'disabled' : ''}>
            下一页
        </button>
    `;
    
    container.innerHTML = html;
}

/**
 * 高级筛选模式下的翻页
 * 
 * @param {number} page - 目标页码
 */
function goToAdvancedFilterPage(page) {
    currentPage = page;
    loadVideosByTagsAdvanced(selectedFilterTagsByCategory, false);
}

/* ==================== 筛选模块 ==================== */

/**
 * 按单个标签筛选视频
 * 
 * 点击标签树中的二级标签时触发。
 * 
 * @param {number} tagId - 标签ID
 * @param {string} tagName - 标签名称
 */
function filterByTag(tagId, tagName) {
    // 更新选中状态
    document.querySelectorAll('.tag-child').forEach(el => {
        el.classList.remove('active');
        if (parseInt(el.dataset.tagId) === tagId) {
            el.classList.add('active');
        }
    });
    
    currentTagIds = [tagId];
    selectedFilterTagsByCategory = {};
    isRandomOrder = false;
    randomSeed = Date.now();
    
    // 显示当前筛选条件
    const filterContainer = document.getElementById('currentFilter');
    filterContainer.style.display = 'flex';
    document.getElementById('filterTags').innerHTML = `
        <span class="filter-tag">${tagName}</span>
    `;
    
    closeMobileSidebar();
    loadVideos(1);
}

/**
 * 清除所有筛选条件
 * 
 * 重置筛选状态并重新加载视频列表。
 */
function clearFilter() {
    currentTagIds = [];
    selectedFilterTags = [];
    selectedFilterTagsByCategory = {};
    randomSeed = Date.now();
    isRandomOrder = false;
    
    document.querySelectorAll('.tag-child').forEach(el => {
        el.classList.remove('active');
    });
    
    document.getElementById('currentFilter').style.display = 'none';
    document.getElementById('clockWallpaperBtn').disabled = true;
    document.getElementById('multiPlayBtn').disabled = true;
    document.getElementById('randomRecommendBtn').disabled = true;
    document.getElementById('shuffleBtn').disabled = true;
    loadVideos(1);
}

/* ==================== 特殊播放模式入口 ==================== */

/**
 * 打开时钟壁纸模式
 * 
 * 跳转到时钟壁纸页面，需要先进行多级筛选。
 */
function openClockWallpaper() {
    if (Object.keys(selectedFilterTagsByCategory).length === 0) {
        showToast('请先进行多级筛选');
        return;
    }
    
    const params = encodeURIComponent(JSON.stringify(selectedFilterTagsByCategory));
    window.location.href = `/clock-wallpaper?filter=${params}`;
}

/**
 * 打开多屏播放模式
 * 
 * 跳转到四屏同时播放页面，需要先进行多级筛选。
 */
function openMultiPlay() {
    if (Object.keys(selectedFilterTagsByCategory).length === 0) {
        showToast('请先进行多级筛选');
        return;
    }
    
    const params = encodeURIComponent(JSON.stringify(selectedFilterTagsByCategory));
    window.location.href = `/multi-play?filter=${params}`;
}

/**
 * 打开随机推荐模式
 * 
 * 跳转到随机推荐播放页面，需要先进行多级筛选。
 */
function openRandomRecommend() {
    if (Object.keys(selectedFilterTagsByCategory).length === 0) {
        showToast('请先进行多级筛选');
        return;
    }
    
    const params = encodeURIComponent(JSON.stringify(selectedFilterTagsByCategory));
    window.location.href = `/random-recommend?filter=${params}`;
}

/* ==================== 搜索模块 ==================== */

/**
 * 搜索视频
 * 
 * 根据关键词搜索视频并更新列表。
 */
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

/* ==================== 视频播放器模块 ==================== */

/**
 * 播放视频
 * 
 * 打开视频播放模态框并初始化 Video.js 播放器。
 * 
 * @param {number} videoId - 视频ID
 * @param {string} title - 视频标题
 * @param {Array} tags - 视频标签列表
 * @param {string} filePath - 视频文件路径
 */
async function playVideo(videoId, title, tags, filePath) {
    try {
        currentVideoPath = filePath;
        
        // 获取视频流信息
        const response = await fetchWithAuth(`/api/video/stream/${videoId}`);
        const result = await response.json();
        
        if (result.success) {
            const modal = document.getElementById('videoModal');
            const formatNotice = document.getElementById('formatNotice');
            
            document.getElementById('modalTitle').textContent = result.data.title;
            
            // 渲染视频标签
            const tagsContainer = document.getElementById('modalTags');
            const childTags = tags.filter(t => t.parent_id);
            tagsContainer.innerHTML = childTags.map(t => 
                `<span class="video-tag">${t.name}</span>`
            ).join('');
            
            // 检查是否为非原生支持格式
            const fileExt = result.data.file_ext || '.mp4';
            const nonNativeFormats = ['.mkv', '.wmv', '.avi'];
            
            if (nonNativeFormats.includes(fileExt)) {
                formatNotice.style.display = 'block';
            } else {
                formatNotice.style.display = 'none';
            }
            
            // 初始化或重置视频播放器
            const playerContainer = document.querySelector('.modal-content');
            let videoElement = document.getElementById('videoPlayer');
            
            // 销毁旧播放器实例
            if (videoPlayer) {
                try {
                    videoPlayer.dispose();
                } catch (e) {
                    console.log('Dispose error:', e);
                }
                videoPlayer = null;
            }
            
            // 创建新的视频元素
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
            
            // 初始化 Video.js 播放器
            videoPlayer = videojs('videoPlayer', {
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
                }
            });
            
            // 设置视频源
            videoPlayer.src({
                src: result.data.stream_url,
                type: getMimeType(fileExt)
            });
            
            // 显示模态框
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
            
            // 尝试自动播放
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

/**
 * 获取文件的 MIME 类型
 * 
 * @param {string} ext - 文件扩展名（包含点号）
 * @returns {string} MIME 类型字符串
 */
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

/**
 * 显示提示消息
 * 
 * 在页面底部显示一个短暂的提示消息。
 * 
 * @param {string} message - 提示消息内容
 */
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

/**
 * 关闭视频播放模态框
 */
function closeVideoModal() {
    const modal = document.getElementById('videoModal');
    
    // 销毁播放器实例
    if (videoPlayer) {
        videoPlayer.pause();
        videoPlayer.dispose();
        videoPlayer = null;
    }
    
    modal.classList.remove('show');
    document.body.style.overflow = '';
}

/* ==================== 键盘事件处理 ==================== */

/**
 * 键盘事件监听
 * 
 * ESC 键关闭所有模态框和侧边栏。
 */
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeVideoModal();
        closeAdvancedFilter();
        closeMobileSidebar();
        closeMobileSearch();
    }
});

/**
 * 模态框点击事件处理
 * 
 * 阻止模态框内容区域的点击事件冒泡，防止误关闭。
 */
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

/* ==================== 统计信息模块 ==================== */

/**
 * 加载统计信息
 * 
 * 从服务器获取视频总数等统计信息并显示。
 */
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

/* ==================== 高级筛选模块 ==================== */

/**
 * 打开高级筛选模态框
 */
function openAdvancedFilter() {
    const modal = document.getElementById('advancedFilterModal');
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    renderFilterTags();
}

/**
 * 关闭高级筛选模态框
 */
function closeAdvancedFilter() {
    const modal = document.getElementById('advancedFilterModal');
    modal.classList.remove('show');
    document.body.style.overflow = '';
}

/**
 * 渲染高级筛选标签列表
 * 
 * 将所有标签按分类渲染为可选择的列表。
 */
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

/**
 * 切换筛选分类的展开/收起状态
 * 
 * @param {HTMLElement} header - 分类标题元素
 */
function toggleFilterCategory(header) {
    const category = header.parentElement;
    category.classList.toggle('collapsed');
}

/**
 * 切换标签选中状态
 * 
 * @param {number} tagId - 标签ID
 * @param {number} categoryId - 所属分类ID
 * @param {string} tagName - 标签名称
 */
function toggleFilterTag(tagId, categoryId, tagName) {
    const index = selectedFilterTags.indexOf(tagId);
    
    if (index === -1) {
        // 添加选中
        selectedFilterTags.push(tagId);
        if (!selectedFilterTagsByCategory[categoryId]) {
            selectedFilterTagsByCategory[categoryId] = [];
        }
        selectedFilterTagsByCategory[categoryId].push(tagId);
    } else {
        // 取消选中
        selectedFilterTags.splice(index, 1);
        if (selectedFilterTagsByCategory[categoryId]) {
            const catIndex = selectedFilterTagsByCategory[categoryId].indexOf(tagId);
            if (catIndex !== -1) {
                selectedFilterTagsByCategory[categoryId].splice(catIndex, 1);
            }
        }
    }
    
    // 更新选中状态样式
    const tagItem = document.querySelector(`.filter-tag-item[data-tag-id="${tagId}"]`);
    if (tagItem) {
        tagItem.classList.toggle('selected');
    }
    
    updateSelectedTagsList();
}

/**
 * 更新已选标签列表显示
 */
function updateSelectedTagsList() {
    const container = document.getElementById('selectedTagsList');
    
    if (selectedFilterTags.length === 0) {
        container.innerHTML = '<span class="no-selection">未选择任何标签</span>';
        return;
    }
    
    // 收集已选标签信息
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

/**
 * 移除单个筛选标签
 * 
 * @param {number} tagId - 标签ID
 * @param {number} categoryId - 所属分类ID
 */
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
    
    // 更新UI状态
    const tagItem = document.querySelector(`.filter-tag-item[data-tag-id="${tagId}"]`);
    if (tagItem) {
        tagItem.classList.remove('selected');
        tagItem.querySelector('input').checked = false;
    }
    
    updateSelectedTagsList();
}

/**
 * 清除所有筛选选择
 */
function clearFilterSelection() {
    selectedFilterTags = [];
    selectedFilterTagsByCategory = {};
    
    document.querySelectorAll('.filter-tag-item.selected').forEach(item => {
        item.classList.remove('selected');
        item.querySelector('input').checked = false;
    });
    
    updateSelectedTagsList();
}

/**
 * 应用高级筛选
 * 
 * 根据选中的标签筛选视频。
 * 支持多分类组合筛选（AND 关系）和同分类内多选（OR 关系）。
 */
async function applyAdvancedFilter() {
    if (selectedFilterTags.length === 0) {
        showToast('请至少选择一个标签');
        return;
    }
    
    closeAdvancedFilter();
    
    currentTagIds = [...selectedFilterTags];
    currentPage = 1;
    isRandomOrder = false;
    randomSeed = Date.now();
    
    // 显示筛选条件
    const filterContainer = document.getElementById('currentFilter');
    const filterTagsSpan = document.getElementById('filterTags');
    
    // 按分类组织筛选条件显示
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
    
    // 生成筛选条件HTML
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
    
    // 启用特殊播放模式按钮
    document.getElementById('clockWallpaperBtn').disabled = false;
    document.getElementById('multiPlayBtn').disabled = false;
    document.getElementById('randomRecommendBtn').disabled = false;
    document.getElementById('shuffleBtn').disabled = false;
    
    await loadVideosByTagsAdvanced(selectedFilterTagsByCategory);
}

/**
 * 随机打乱视频顺序
 * 
 * 生成新的随机种子，对所有筛选结果进行整体随机排序，
 * 然后从第一页开始显示。
 */
async function shuffleVideos() {
    if (Object.keys(selectedFilterTagsByCategory).length === 0) {
        return;
    }
    
    const shuffleBtn = document.getElementById('shuffleBtn');
    shuffleBtn.classList.add('shuffling');
    
    randomSeed = Date.now();
    isRandomOrder = true;
    currentPage = 1;
    
    await loadVideosByTagsAdvanced(selectedFilterTagsByCategory, true);
    
    setTimeout(() => {
        shuffleBtn.classList.remove('shuffling');
    }, 300);
}

/**
 * 按高级筛选条件加载视频
 * 
 * @param {Object} tagsByCategory - 按分类分组的标签 {categoryId: [tagId, ...]}
 * @param {boolean} shuffle - 是否随机打乱顺序
 */
async function loadVideosByTagsAdvanced(tagsByCategory, shuffle = false) {
    const container = document.getElementById('videoGrid');
    container.innerHTML = '<div class="loading">加载中...</div>';
    
    try {
        const requestBody = {
            tags_by_category: tagsByCategory,
            page: currentPage,
            page_size: 50
        };
        
        if (shuffle || isRandomOrder) {
            requestBody.random_order = true;
            requestBody.random_seed = randomSeed;
        }
        
        const response = await fetchWithAuth('/api/videos/by-tags-advanced', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
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

/**
 * 随机打乱数组
 * 
 * 使用 Fisher-Yates 算法随机打乱数组顺序。
 * 
 * @param {Array} array - 要打乱的数组
 * @returns {Array} 打乱后的新数组
 */
function shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

/* ==================== 滚动事件处理 ==================== */

/** 上次滚动位置 */
let lastScrollTop = 0;

/** 导航栏元素 */
const navbar = document.querySelector('.navbar');

/**
 * 滚动事件监听
 * 
 * 在移动端实现导航栏自动隐藏/显示效果。
 */
window.addEventListener('scroll', function() {
    if (window.innerWidth <= 768) {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // 向下滚动超过100px时隐藏导航栏
        if (scrollTop > lastScrollTop && scrollTop > 100) {
            navbar.style.transform = 'translateY(-100%)';
        } else {
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
    }
}, { passive: true });

/**
 * 窗口大小变化事件监听
 * 
 * 当窗口宽度超过移动端阈值时，关闭移动端特有的UI组件。
 */
window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
        closeMobileSidebar();
        closeMobileSearch();
        navbar.style.transform = 'translateY(0)';
    }
});

/* ==================== 会话超时管理 ==================== */

const SESSION_TIMEOUT = 10 * 60 * 1000;
let lastActivityTime = Date.now();
let sessionTimerInterval = null;
let sessionWarningShown = false;

function initSessionTimeout() {
    const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
    
    activityEvents.forEach(event => {
        document.addEventListener(event, handleUserActivity, { passive: true });
    });
    
    sessionTimerInterval = setInterval(checkSessionTimeout, 1000);
    
    updateSessionTimer();
}

function handleUserActivity() {
    lastActivityTime = Date.now();
    sessionWarningShown = false;
}

function checkSessionTimeout() {
    const elapsed = Date.now() - lastActivityTime;
    const remaining = SESSION_TIMEOUT - elapsed;
    
    updateSessionTimer();
    
    if (remaining <= 60000 && remaining > 30000 && !sessionWarningShown) {
        showSessionWarning(Math.ceil(remaining / 1000));
        sessionWarningShown = true;
    }
    
    if (remaining <= 0) {
        clearInterval(sessionTimerInterval);
        logout(true);
    }
}

function updateSessionTimer() {
    const timerEl = document.getElementById('sessionTimer');
    if (!timerEl) return;
    
    const elapsed = Date.now() - lastActivityTime;
    const remaining = Math.max(0, SESSION_TIMEOUT - elapsed);
    const minutes = Math.floor(remaining / 60000);
    const seconds = Math.floor((remaining % 60000) / 1000);
    
    timerEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    
    timerEl.classList.remove('warning', 'danger');
    if (remaining <= 60000) {
        timerEl.classList.add('danger');
    } else if (remaining <= 180000) {
        timerEl.classList.add('warning');
    }
}

function showSessionWarning(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    showToast(`会话将在 ${minutes}分${secs}秒 后过期，请继续操作以保持登录`, 'warning');
}

function logout(timeout = false) {
    if (sessionTimerInterval) {
        clearInterval(sessionTimerInterval);
    }
    
    if (timeout) {
        alert('由于长时间未操作，您已自动退出登录');
    }
    
    window.location.href = '/logout';
}
