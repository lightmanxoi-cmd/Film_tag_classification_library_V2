/**
 * 分页渲染模块
 */

import { appState } from '../stores/state.js';

export function renderPagination(data, containerId = 'pagination', options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (data.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    const onPageChange = options.onPageChange || (() => {});
    const currentPage = data.page;
    const totalPages = data.total_pages;
    const total = data.total;
    
    const prevBtn = createPaginationButton('上一页', currentPage - 1, currentPage <= 1, onPageChange);
    const nextBtn = createPaginationButton('下一页', currentPage + 1, currentPage >= totalPages, onPageChange);
    const pageInfo = document.createElement('span');
    pageInfo.className = 'page-info';
    pageInfo.textContent = `第 ${currentPage} / ${totalPages} 页 (共 ${total} 部)`;
    
    container.innerHTML = '';
    container.appendChild(prevBtn);
    container.appendChild(pageInfo);
    container.appendChild(nextBtn);
}

function createPaginationButton(text, page, disabled, onPageChange) {
    const btn = document.createElement('button');
    btn.textContent = text;
    btn.disabled = disabled;
    if (!disabled) {
        btn.addEventListener('click', () => onPageChange(page));
    }
    return btn;
}

export function createPaginationOnClick(page, isAdvancedFilter, selectedFilterTagsByCategory) {
    if (isAdvancedFilter && Object.keys(selectedFilterTagsByCategory).length > 0) {
        return `goToAdvancedFilterPage(${page})`;
    }
    return `loadVideos(${page})`;
}
