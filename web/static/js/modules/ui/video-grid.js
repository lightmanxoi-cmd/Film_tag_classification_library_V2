/**
 * 视频卡片渲染模块
 */

import { setupLazyLoading } from '../utils/lazy-load.js';

export function renderVideos(videos, containerId = 'videoGrid', options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (videos.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>没有找到视频</h3>
                <p>请尝试其他筛选条件</p>
            </div>
        `;
        return;
    }
    
    const isMobile = window.innerWidth <= 1023;
    const onVideoClick = options.onVideoClick || (() => {});
    
    container.innerHTML = '';
    
    videos.forEach(video => {
        const card = createVideoCard(video, isMobile);
        card.addEventListener('click', () => onVideoClick(video));
        container.appendChild(card);
    });
    
    setupLazyLoading('.thumbnail[data-bg-image], .gif-preview[data-src], .gif-preview-mobile[data-src]', {
        rootMargin: '200px'
    });
}

function createVideoCard(video, isMobile) {
    const card = document.createElement('div');
    card.className = 'video-card';
    card.dataset.videoId = video.id;
    
    const ext = video.file_path.split('.').pop().toLowerCase();
    const formatClass = ['mkv', 'wmv', 'avi'].includes(ext) ? 'non-native' : '';
    
    const childTags = video.tags.filter(t => t.parent_id);
    const tagsHtml = childTags.slice(0, 3).map(t => 
        `<span class="video-tag">${t.name}</span>`
    ).join('');
    
    const thumbnailHtml = createThumbnailHtml(video, ext, formatClass, isMobile);
    
    card.innerHTML = `
        ${thumbnailHtml}
        <div class="video-overlay">
            <div class="video-title">${video.title}</div>
            <div class="video-tags">${tagsHtml}</div>
        </div>
    `;
    
    if (!isMobile && video.gif) {
        setupGifHover(card, video);
    }
    
    return card;
}

function createThumbnailHtml(video, ext, formatClass, isMobile) {
    // 对URL进行编码，处理特殊字符如 #
    const encodedGif = video.gif ? encodeURI(video.gif) : null;
    const encodedThumbnail = video.thumbnail ? encodeURI(video.thumbnail) : null;
    
    if (isMobile && encodedGif) {
        return `
            <div class="thumbnail gif-mode ${formatClass}">
                <img class="gif-preview-mobile lazy-loading" 
                     data-src="${encodedGif}" 
                     alt="${video.title}"
                     loading="lazy">
                <span class="play-overlay">▶</span>
                <span class="format-badge">${ext.toUpperCase()}</span>
            </div>
        `;
    }
    
    const thumbnailClass = encodedThumbnail ? 'thumbnail lazy-loading' : 'thumbnail';
    const thumbnailDataAttr = encodedThumbnail ? 
        `data-bg-image="url('${encodedThumbnail}')"` : '';
    
    const gifElement = encodedGif ? 
        `<img class="gif-preview lazy-loading" data-src="${encodedGif}" alt="${video.title}" style="display: none;">` : '';
    
    return `
        <div class="${thumbnailClass} ${formatClass}" ${thumbnailDataAttr}>
            ${!encodedThumbnail ? '<span class="play-icon">▶</span>' : '<span class="play-overlay">▶</span>'}
            <span class="format-badge">${ext.toUpperCase()}</span>
            ${gifElement}
        </div>
    `;
}

function setupGifHover(card, video) {
    const thumbnailDiv = card.querySelector('.thumbnail');
    const gifImg = card.querySelector('.gif-preview');
    // 对缩略图URL进行编码
    const encodedThumbnail = video.thumbnail ? encodeURI(video.thumbnail) : null;
    
    card.addEventListener('mouseenter', () => {
        thumbnailDiv.style.backgroundImage = 'none';
        gifImg.style.display = 'block';
        if (gifImg.dataset.src) {
            gifImg.src = gifImg.dataset.src;
            gifImg.removeAttribute('data-src');
            gifImg.classList.remove('lazy-loading');
            gifImg.classList.add('lazy-loaded');
        }
    });
    
    card.addEventListener('mouseleave', () => {
        gifImg.style.display = 'none';
        if (encodedThumbnail) {
            thumbnailDiv.style.backgroundImage = `url('${encodedThumbnail}')`;
        }
    });
}

export function showLoading(containerId = 'videoGrid', message = '加载中...') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `<div class="loading">${message}</div>`;
    }
}

export function showError(containerId = 'videoGrid', message = '加载失败') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `<div class="loading">${message}</div>`;
    }
}
