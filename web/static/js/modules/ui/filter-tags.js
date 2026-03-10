/**
 * 筛选标签渲染模块
 */

import { appState } from '../stores/state.js';

export function renderFilterTags(tags, containerId = 'filterTagsContainer') {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const filterTags = appState.get('selectedFilterTags');
    const filterTagsByCategory = appState.get('selectedFilterTagsByCategory');
    
    if (!tags || tags.length === 0) {
        container.innerHTML = '<div class="loading">请等待标签加载...</div>';
        return;
    }
    
    container.innerHTML = '';
    
    tags.forEach(category => {
        const categoryDiv = createFilterCategory(category, filterTags, filterTagsByCategory);
        container.appendChild(categoryDiv);
    });
}

function createFilterCategory(category, filterTags, filterTagsByCategory) {
    const categoryDiv = document.createElement('div');
    categoryDiv.className = 'filter-category';
    
    categoryDiv.innerHTML = `
        <div class="filter-category-header">
            <span class="toggle-icon">▼</span>
            <h4>${category.name}</h4>
        </div>
        <div class="filter-category-tags">
            ${category.children.map(tag => `
                <label class="filter-tag-item ${filterTags.includes(tag.id) ? 'selected' : ''}" 
                       data-tag-id="${tag.id}" 
                       data-category-id="${category.id}">
                    <input type="checkbox" 
                           ${filterTags.includes(tag.id) ? 'checked' : ''}>
                    <span>${tag.name}</span>
                    <span class="tag-count">${tag.video_count || 0}</span>
                </label>
            `).join('')}
        </div>
    `;
    
    const header = categoryDiv.querySelector('.filter-category-header');
    header.addEventListener('click', () => {
        categoryDiv.classList.toggle('collapsed');
    });
    
    categoryDiv.querySelectorAll('.filter-tag-item').forEach(item => {
        const checkbox = item.querySelector('input');
        const tagId = parseInt(item.dataset.tagId);
        const categoryId = parseInt(item.dataset.categoryId);
        
        checkbox.addEventListener('change', () => {
            toggleFilterTagUI(item, tagId, categoryId);
        });
    });
    
    return categoryDiv;
}

function toggleFilterTagUI(item, tagId, categoryId) {
    if (item.classList.contains('selected')) {
        appState.removeFilterTag(tagId, categoryId);
        item.classList.remove('selected');
    } else {
        appState.addFilterTag(tagId, categoryId);
        item.classList.add('selected');
    }
    
    updateSelectedTagsList();
}

export function updateSelectedTagsList(containerId = 'selectedTagsList') {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const filterTags = appState.get('selectedFilterTags');
    const allTags = appState.get('allTags');
    
    if (filterTags.length === 0) {
        container.innerHTML = '<span class="no-selection">未选择任何标签</span>';
        return;
    }
    
    const selectedTagsInfo = [];
    allTags.forEach(category => {
        category.children.forEach(tag => {
            if (filterTags.includes(tag.id)) {
                selectedTagsInfo.push({ id: tag.id, name: tag.name, categoryId: category.id });
            }
        });
    });
    
    container.innerHTML = selectedTagsInfo.map(tag => `
        <span class="selected-tag-chip">
            ${tag.name}
            <span class="remove-tag" data-tag-id="${tag.id}" data-category-id="${tag.categoryId}">×</span>
        </span>
    `).join('');
    
    container.querySelectorAll('.remove-tag').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tagId = parseInt(btn.dataset.tagId);
            const categoryId = parseInt(btn.dataset.categoryId);
            removeFilterTagUI(tagId, categoryId);
        });
    });
}

function removeFilterTagUI(tagId, categoryId) {
    appState.removeFilterTag(tagId, categoryId);
    
    const tagItem = document.querySelector(`.filter-tag-item[data-tag-id="${tagId}"]`);
    if (tagItem) {
        tagItem.classList.remove('selected');
        tagItem.querySelector('input').checked = false;
    }
    
    updateSelectedTagsList();
}

export function clearFilterSelectionUI() {
    appState.setMultiple({
        selectedFilterTags: [],
        selectedFilterTagsByCategory: {}
    });
    
    document.querySelectorAll('.filter-tag-item.selected').forEach(item => {
        item.classList.remove('selected');
        item.querySelector('input').checked = false;
    });
    
    updateSelectedTagsList();
}

export function renderCurrentFilter(filterTagsByCategory, allTags, containerId = 'filterTags') {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const categoryGroups = [];
    allTags.forEach(category => {
        const selectedInCategory = (filterTagsByCategory[category.id] || []);
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
    
    container.innerHTML = filterHtml;
}
