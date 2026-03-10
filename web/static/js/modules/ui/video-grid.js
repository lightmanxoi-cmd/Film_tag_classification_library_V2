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
    if (isMobile && video.gif) {
        return `
            <div class="thumbnail gif-mode ${formatClass}">
                <img class="gif-preview-mobile lazy-loading" 
                     data-src="${video.gif}" 
                     alt="${video.title}"
                     loading="lazy">
                <span class="play-overlay">▶</span>
                <span class="format-badge">${ext.toUpperCase()}</span>
            </div>
        `;
    }
    
    const thumbnailClass = video.thumbnail ? 'thumbnail lazy-loading' : 'thumbnail';
    const thumbnailDataAttr = video.thumbnail ? 
        `data-bg-image="url('${video.thumbnail}')"` : '';
    
    const gifElement = video.gif ? 
        `<img class="gif-preview lazy-loading" data-src="${video.gif}" alt="${video.title}" style="display: none;">` : '';
    
    return `
        <div class="${thumbnailClass} ${formatClass}" ${thumbnailDataAttr}>
            ${!video.thumbnail ? '<span class="play-icon">▶</span>' : '<span class="play-overlay">▶</span>'}
            <span class="format-badge">${ext.toUpperCase()}</span>
            ${gifElement}
        </div>
    `;
}

function setupGifHover(card, video) {
    const thumbnailDiv = card.querySelector('.thumbnail');
    const gifImg = card.querySelector('.gif-preview');
    
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
        if (video.thumbnail) {
            thumbnailDiv.style.backgroundImage = `url('${video.thumbnail}')`;
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
