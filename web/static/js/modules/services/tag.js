/**
 * 标签服务模块
 */

import { fetchWithAuth } from '../api/fetch.js';
import { appState } from '../stores/state.js';

class TagService {
    async loadTagTree() {
        try {
            const response = await fetchWithAuth('/api/tags/tree');
            const result = await response.json();
            
            if (result.success) {
                appState.set('allTags', result.data);
                return result.data;
            }
            throw new Error(result.message || '加载标签树失败');
        } catch (error) {
            console.error('加载标签树失败:', error);
            throw error;
        }
    }
    
    getTagById(tagId) {
        const allTags = appState.get('allTags');
        for (const category of allTags) {
            if (category.id === tagId) return category;
            if (category.children) {
                const found = category.children.find(t => t.id === tagId);
                if (found) return found;
            }
        }
        return null;
    }
    
    getTagNameById(tagId) {
        const tag = this.getTagById(tagId);
        return tag ? tag.name : '';
    }
    
    filterByTag(tagId, tagName) {
        appState.setMultiple({
            currentTagIds: [tagId],
            selectedFilterTagsByCategory: {},
            isRandomOrder: false,
            randomSeed: Date.now()
        });
        
        return { tagId, tagName };
    }
    
    clearFilter() {
        appState.resetFilter();
    }
}

export const tagService = new TagService();
