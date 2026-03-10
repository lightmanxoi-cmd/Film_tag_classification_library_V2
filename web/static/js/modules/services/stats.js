/**
 * 统计服务模块
 */

import { fetchWithAuth } from '../api/fetch.js';

class StatsService {
    async loadStats() {
        try {
            const response = await fetchWithAuth('/api/stats');
            const result = await response.json();
            
            if (result.success) {
                return result.data;
            }
            throw new Error(result.message || '加载统计信息失败');
        } catch (error) {
            console.error('加载统计信息失败:', error);
            throw error;
        }
    }
    
    updateVideoCount(count) {
        const el = document.getElementById('videoCount');
        if (el) {
            el.textContent = count;
        }
    }
}

export const statsService = new StatsService();
