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
            isRandomOrder: false
        };
        this._listeners = new Map();
    }

    get(key) {
        return this._state[key];
    }

    set(key, value) {
        const oldValue = this._state[key];
        this._state[key] = value;
        this._notify(key, value, oldValue);
    }

    getAll() {
        return { ...this._state };
    }

    subscribe(key, callback) {
        if (!this._listeners.has(key)) {
            this._listeners.set(key, new Set());
        }
        this._listeners.get(key).add(callback);
        return () => this._listeners.get(key).delete(callback);
    }

    _notify(key, newValue, oldValue) {
        if (this._listeners.has(key)) {
            this._listeners.get(key).forEach(callback => {
                callback(newValue, oldValue);
            });
        }
    }

    reset() {
        this._state.currentPage = 1;
        this._state.currentTagIds = [];
        this._state.selectedFilterTags = [];
        this._state.selectedFilterTagsByCategory = {};
        this._state.randomSeed = Date.now();
        this._state.isRandomOrder = false;
        this._notify('reset', this._state, null);
    }

    resetFilter() {
        this._state.currentTagIds = [];
        this._state.selectedFilterTags = [];
        this._state.selectedFilterTagsByCategory = {};
        this._state.randomSeed = Date.now();
        this._state.isRandomOrder = false;
        this._notify('filterReset', this._state, null);
    }

    addFilterTag(tagId, categoryId) {
        const tags = this._state.selectedFilterTags;
        if (!tags.includes(tagId)) {
            tags.push(tagId);
        }

        const byCategory = this._state.selectedFilterTagsByCategory;
        if (!byCategory[categoryId]) {
            byCategory[categoryId] = [];
        }
        if (!byCategory[categoryId].includes(tagId)) {
            byCategory[categoryId].push(tagId);
        }

        this._notify('filterTagsChanged', this._state.selectedFilterTags, null);
    }

    removeFilterTag(tagId, categoryId) {
        const tags = this._state.selectedFilterTags;
        const index = tags.indexOf(tagId);
        if (index > -1) {
            tags.splice(index, 1);
        }

        const byCategory = this._state.selectedFilterTagsByCategory;
        if (byCategory[categoryId]) {
            const catIndex = byCategory[categoryId].indexOf(tagId);
            if (catIndex > -1) {
                byCategory[categoryId].splice(catIndex, 1);
            }
        }

        this._notify('filterTagsChanged', this._state.selectedFilterTags, null);
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
    IS_RANDOM_ORDER: 'isRandomOrder'
};
