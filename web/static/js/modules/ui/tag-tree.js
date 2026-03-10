/**
 * 标签树渲染模块
 */

import { appState } from '../stores/state.js';

export function renderTagTree(tags, containerId = 'tagTree') {
    const container = document.getElementById(containerId);
    if (!container) return;
    
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
                    const event = new CustomEvent('tag-selected', {
                        detail: { tagId: child.id, tagName: child.name }
                    });
                    document.dispatchEvent(event);
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

export function highlightActiveTag(tagId) {
    document.querySelectorAll('.tag-child').forEach(el => {
        el.classList.remove('active');
        if (parseInt(el.dataset.tagId) === tagId) {
            el.classList.add('active');
        }
    });
}

export function clearActiveTags() {
    document.querySelectorAll('.tag-child').forEach(el => {
        el.classList.remove('active');
    });
}
