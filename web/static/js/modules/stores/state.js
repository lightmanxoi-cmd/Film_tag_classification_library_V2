/**
 * 应用状态管理模块
 * 
 * 集中管理应用的全局状态，提供响应式更新能力
 */

class AppState {
    constructor() {
        this._state = {
            currentPage: 1,
            currentTagIds: [],
            allTags: [],
            selectedFilterTags: [],
            selectedFilterTagsByCategory: {},
            randomSeed: Date.now(),
            isRandomOrder: false,
            videoPlayer: null,
            currentVideoPath: '',
            currentVideoId: null,
            currentVideoTitle: '',
            currentVideoTags: [],
            isLoading: false,
            searchQuery: '',
            sidebarOpen: false,
            filterModalOpen: false
        };
        this._listeners = new Map();
        this._history = [];
        this._maxHistory = 50;
    }

    get(key) {
        return this._state[key];
    }

    set(key, value) {
        const oldValue = this._state[key];
        if (oldValue === value) return;
        
        this._state[key] = value;
        this._notify(key, value, oldValue);
    }

    getAll() {
        return { ...this._state };
    }

    setMultiple(updates) {
        const oldValues = {};
        Object.keys(updates).forEach(key => {
            oldValues[key] = this._state[key];
            this._state[key] = updates[key];
        });
        
        Object.keys(updates).forEach(key => {
            this._notify(key, updates[key], oldValues[key]);
        });
    }

    subscribe(key, callback) {
        if (!this._listeners.has(key)) {
            this._listeners.set(key, new Set());
        }
        this._listeners.get(key).add(callback);
        return () => this._listeners.get(key).delete(callback);
    }

    subscribeMultiple(keys, callback) {
        const unsubscribers = keys.map(key => this.subscribe(key, callback));
        return () => unsubscribers.forEach(unsub => unsub());
    }

    _notify(key, newValue, oldValue) {
        if (this._listeners.has(key)) {
            this._listeners.get(key).forEach(callback => {
                try {
                    callback(newValue, oldValue, key);
                } catch (e) {
                    console.error(`[AppState] Listener error for ${key}:`, e);
                }
            });
        }
    }

    reset() {
        const oldState = { ...this._state };
        this._state = {
            currentPage: 1,
            currentTagIds: [],
            allTags: oldState.allTags,
            selectedFilterTags: [],
            selectedFilterTagsByCategory: {},
            randomSeed: Date.now(),
            isRandomOrder: false,
            videoPlayer: null,
            currentVideoPath: '',
            currentVideoId: null,
            currentVideoTitle: '',
            currentVideoTags: [],
            isLoading: false,
            searchQuery: '',
            sidebarOpen: false,
            filterModalOpen: false
        };
        this._notify('reset', this._state, oldState);
    }

    resetFilter() {
        this.setMultiple({
            currentTagIds: [],
            selectedFilterTags: [],
            selectedFilterTagsByCategory: {},
            randomSeed: Date.now(),
            isRandomOrder: false
        });
        this._notify('filterReset', null, null);
    }

    addFilterTag(tagId, categoryId) {
        const tags = [...this._state.selectedFilterTags];
        if (!tags.includes(tagId)) {
            tags.push(tagId);
        }

        const byCategory = { ...this._state.selectedFilterTagsByCategory };
        if (!byCategory[categoryId]) {
            byCategory[categoryId] = [];
        }
        if (!byCategory[categoryId].includes(tagId)) {
            byCategory[categoryId] = [...byCategory[categoryId], tagId];
        }

        this.setMultiple({
            selectedFilterTags: tags,
            selectedFilterTagsByCategory: byCategory
        });
    }

    removeFilterTag(tagId, categoryId) {
        const tags = this._state.selectedFilterTags.filter(t => t !== tagId);

        const byCategory = { ...this._state.selectedFilterTagsByCategory };
        if (byCategory[categoryId]) {
            byCategory[categoryId] = byCategory[categoryId].filter(t => t !== tagId);
            if (byCategory[categoryId].length === 0) {
                delete byCategory[categoryId];
            }
        }

        this.setMultiple({
            selectedFilterTags: tags,
            selectedFilterTagsByCategory: byCategory
        });
    }

    setCurrentVideo(video) {
        this.setMultiple({
            currentVideoId: video.id,
            currentVideoTitle: video.title,
            currentVideoTags: video.tags,
            currentVideoPath: video.path
        });
    }

    clearCurrentVideo() {
        this.setMultiple({
            currentVideoId: null,
            currentVideoTitle: '',
            currentVideoTags: [],
            currentVideoPath: ''
        });
    }

    setLoading(loading) {
        this.set('isLoading', loading);
    }

    toggleSidebar() {
        this.set('sidebarOpen', !this._state.sidebarOpen);
    }

    toggleFilterModal() {
        this.set('filterModalOpen', !this._state.filterModalOpen);
    }

    persist(key = 'appState') {
        try {
            const persistableState = {
                currentPage: this._state.currentPage,
                randomSeed: this._state.randomSeed,
                isRandomOrder: this._state.isRandomOrder
            };
            localStorage.setItem(key, JSON.stringify(persistableState));
        } catch (e) {
            console.warn('[AppState] Failed to persist state:', e);
        }
    }

    restore(key = 'appState') {
        try {
            const saved = localStorage.getItem(key);
            if (saved) {
                const parsed = JSON.parse(saved);
                this.setMultiple(parsed);
                return true;
            }
        } catch (e) {
            console.warn('[AppState] Failed to restore state:', e);
        }
        return false;
    }

    createComputed(computeFn, dependencies) {
        let cachedValue = computeFn(this._state);
        
        const unsubscribe = this.subscribeMultiple(dependencies, () => {
            cachedValue = computeFn(this._state);
        });

        return {
            get: () => cachedValue,
            destroy: unsubscribe
        };
    }
}

export const appState = new AppState();

export const stateKeys = {
    CURRENT_PAGE: 'currentPage',
    CURRENT_TAG_IDS: 'currentTagIds',
    ALL_TAGS: 'allTags',
    SELECTED_FILTER_TAGS: 'selectedFilterTags',
    SELECTED_FILTER_TAGS_BY_CATEGORY: 'selectedFilterTagsByCategory',
    RANDOM_SEED: 'randomSeed',
    IS_RANDOM_ORDER: 'isRandomOrder',
    VIDEO_PLAYER: 'videoPlayer',
    CURRENT_VIDEO_PATH: 'currentVideoPath',
    CURRENT_VIDEO_ID: 'currentVideoId',
    CURRENT_VIDEO_TITLE: 'currentVideoTitle',
    CURRENT_VIDEO_TAGS: 'currentVideoTags',
    IS_LOADING: 'isLoading',
    SEARCH_QUERY: 'searchQuery',
    SIDEBAR_OPEN: 'sidebarOpen',
    FILTER_MODAL_OPEN: 'filterModalOpen'
};
