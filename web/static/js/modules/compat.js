/**
 * 兼容层
 * 
 * 将 ES6 模块导出的函数挂载到全局对象上，
 * 实现渐进式迁移，保持向后兼容
 */

import { 
    fetchWithAuth, 
    fetchJSON, 
    postJSON 
} from './api/index.js';

import { 
    formatTime, 
    formatVideoCount, 
    formatVideoCountEn, 
    formatFileSize,
    getUrlParams, 
    getQueryParam, 
    setQueryParam, 
    buildQueryString, 
    encodeFilterParams,
    shuffleArray, 
    createShuffledIndices, 
    uniqueBy, 
    groupBy,
    sessionManager, 
    initSessionTimeout,
    initTouchGestures, 
    initSwipeToClose 
} from './utils/index.js';

import { 
    showToast, 
    showSuccess, 
    showWarning, 
    showError,
    VideoPlayer, 
    getMimeType, 
    isNonNativeFormat 
} from './components/index.js';

import { appState, stateKeys } from './stores/state.js';

window.fetchWithAuth = fetchWithAuth;
window.fetchJSON = fetchJSON;
window.postJSON = postJSON;

window.formatTime = formatTime;
window.formatVideoCount = formatVideoCount;
window.formatVideoCountEn = formatVideoCountEn;
window.formatFileSize = formatFileSize;

window.getUrlParams = getUrlParams;
window.getQueryParam = getQueryParam;
window.setQueryParam = setQueryParam;
window.buildQueryString = buildQueryString;
window.encodeFilterParams = encodeFilterParams;

window.shuffleArray = shuffleArray;
window.createShuffledIndices = createShuffledIndices;
window.uniqueBy = uniqueBy;
window.groupBy = groupBy;

window.sessionManager = sessionManager;
window.initSessionTimeout = initSessionTimeout;

window.initTouchGestures = initTouchGestures;
window.initSwipeToClose = initSwipeToClose;

window.showToast = showToast;
window.showSuccess = showSuccess;
window.showWarning = showWarning;
window.showError = showError;

window.VideoPlayer = VideoPlayer;
window.getMimeType = getMimeType;
window.isNonNativeFormat = isNonNativeFormat;

window.appState = appState;
window.stateKeys = stateKeys;

console.log('[Modules] 兼容层已加载，模块已挂载到全局对象');
