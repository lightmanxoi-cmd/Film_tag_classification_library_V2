/**
 * 视频服务模块
 */

import { fetchWithAuth, postJSON } from '../api/fetch.js';
import { appState } from '../stores/state.js';

class VideoService {
    async loadVideos(page = 1) {
        appState.set('currentPage', page);
        const currentTagIds = appState.get('currentTagIds');
        const pageSize = this.getPageSize();
        
        try {
            let result;
            
            if (currentTagIds.length > 0) {
                result = await postJSON('/api/videos/by-tags', {
                    tag_ids: currentTagIds,
                    page: page,
                    page_size: pageSize,
                    match_all: false
                });
            } else {
                const randomSeed = appState.get('randomSeed');
                const response = await fetchWithAuth(
                    `/api/videos?page=${page}&page_size=${pageSize}&random=true&seed=${randomSeed}`
                );
                result = await response.json();
            }
            
            if (result.success) {
                return result.data;
            }
            throw new Error(result.message || '加载失败');
        } catch (error) {
            console.error('加载视频失败:', error);
            throw error;
        }
    }
    
    async loadVideosByTagsAdvanced(tagsByCategory, shuffle = false) {
        const page = appState.get('currentPage');
        const pageSize = this.getPageSize();
        
        const requestBody = {
            tags_by_category: tagsByCategory,
            page: page,
            page_size: pageSize
        };
        
        if (shuffle || appState.get('isRandomOrder')) {
            requestBody.random_order = true;
            requestBody.random_seed = appState.get('randomSeed');
        }
        
        try {
            const result = await postJSON('/api/videos/by-tags-advanced', requestBody);
            
            if (result.success) {
                return result.data;
            }
            throw new Error(result.message || '加载失败');
        } catch (error) {
            console.error('加载视频失败:', error);
            throw error;
        }
    }
    
    async searchVideos(keyword, page = 1) {
        const pageSize = this.getPageSize();
        
        try {
            const response = await fetchWithAuth(
                `/api/videos?page=${page}&page_size=${pageSize}&search=${encodeURIComponent(keyword)}`
            );
            const result = await response.json();
            
            if (result.success) {
                return result.data;
            }
            throw new Error(result.message || '搜索失败');
        } catch (error) {
            console.error('搜索失败:', error);
            throw error;
        }
    }
    
    async getVideoStreamUrl(videoId) {
        try {
            const response = await fetchWithAuth(`/api/video/stream/${videoId}`);
            const result = await response.json();
            
            if (result.success) {
                return result.data;
            }
            throw new Error(result.message || '获取视频信息失败');
        } catch (error) {
            console.error('获取视频信息失败:', error);
            throw error;
        }
    }
    
    getPageSize() {
        const isMobile = window.innerWidth <= 1023;
        return isMobile ? 20 : 50;
    }
}

export const videoService = new VideoService();
