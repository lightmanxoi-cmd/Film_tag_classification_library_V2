/**
 * 图片懒加载模块
 * 
 * 使用 Intersection Observer API 实现高性能图片懒加载
 * 支持移动端优化、网络状态感知、优先级加载
 */

let observer = null;
let preloadQueue = [];
let isProcessingQueue = false;

const defaultOptions = {
    rootMargin: '200px 0px',
    threshold: 0.1
};

const mobileOptions = {
    rootMargin: '300px 0px',
    threshold: 0.05
};

function isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) 
        || window.innerWidth < 1024;
}

function getConnectionInfo() {
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (connection) {
        return {
            effectiveType: connection.effectiveType,
            downlink: connection.downlink,
            saveData: connection.saveData
        };
    }
    return { effectiveType: '4g', downlink: 10, saveData: false };
}

function getOptimalQuality() {
    const { effectiveType, saveData, downlink } = getConnectionInfo();
    
    if (saveData) return 'low';
    if (effectiveType === 'slow-2g' || effectiveType === '2g') return 'low';
    if (effectiveType === '3g') return 'medium';
    return 'high';
}

function createObserver(options = {}) {
    if (observer) {
        return observer;
    }
    
    const baseOptions = isMobile() ? mobileOptions : defaultOptions;
    const config = { ...baseOptions, ...options };
    
    observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                const priority = element.dataset.priority || 'normal';
                
                if (priority === 'high') {
                    loadImage(element);
                } else {
                    addToQueue(element);
                }
                observer.unobserve(element);
            }
        });
    }, config);
    
    return observer;
}

function addToQueue(element) {
    preloadQueue.push(element);
    
    if (!isProcessingQueue) {
        processQueue();
    }
}

function processQueue() {
    if (preloadQueue.length === 0) {
        isProcessingQueue = false;
        return;
    }
    
    isProcessingQueue = true;
    
    const batchSize = isMobile() ? 2 : 4;
    const batch = preloadQueue.splice(0, batchSize);
    
    batch.forEach(element => {
        requestAnimationFrame(() => {
            loadImage(element);
        });
    });
    
    if (preloadQueue.length > 0) {
        if (isMobile()) {
            requestIdleCallback(() => processQueue(), { timeout: 100 });
        } else {
            requestAnimationFrame(() => processQueue());
        }
    } else {
        isProcessingQueue = false;
    }
}

function loadImage(element) {
    if (element.tagName === 'IMG') {
        const src = element.dataset.src;
        const srcset = element.dataset.srcset;
        const quality = element.dataset.quality || getOptimalQuality();
        
        if (src) {
            const optimizedSrc = getOptimizedUrl(src, quality);
            
            const img = new Image();
            img.onload = () => {
                element.src = optimizedSrc;
                element.removeAttribute('data-src');
                element.classList.add('lazy-loaded');
                element.classList.remove('lazy-loading');
                
                element.dispatchEvent(new CustomEvent('lazyloaded', {
                    bubbles: true,
                    detail: { src: optimizedSrc }
                }));
            };
            img.onerror = () => {
                element.classList.remove('lazy-loading');
                element.classList.add('lazy-error');
                
                if (element.dataset.fallback) {
                    element.src = element.dataset.fallback;
                }
            };
            img.src = optimizedSrc;
        }
        
        if (srcset) {
            element.srcset = srcset;
            element.removeAttribute('data-srcset');
        }
    } else if (element.dataset.bgImage) {
        const quality = element.dataset.quality || getOptimalQuality();
        const optimizedUrl = getOptimizedUrl(
            element.dataset.bgImage.match(/url\(['"]?([^'"]+)['"]?\)/)?.[1] || '',
            quality
        );
        
        const img = new Image();
        img.onload = () => {
            element.style.backgroundImage = `url('${optimizedUrl}')`;
            element.removeAttribute('data-bg-image');
            element.classList.add('lazy-loaded');
            element.classList.remove('lazy-loading');
            
            element.dispatchEvent(new CustomEvent('lazyloaded', {
                bubbles: true,
                detail: { src: optimizedUrl }
            }));
        };
        img.onerror = () => {
            element.classList.remove('lazy-loading');
            element.classList.add('lazy-error');
        };
        img.src = optimizedUrl;
    }
}

function getOptimizedUrl(url, quality) {
    if (!url || url.startsWith('data:')) return url;
    
    return url;
}

export function setupLazyLoading(selector = 'img[data-src], [data-bg-image]', options = {}) {
    const obs = createObserver(options);
    
    const elements = document.querySelectorAll(selector);
    elements.forEach(element => {
        if (!element.classList.contains('lazy-loaded')) {
            element.classList.add('lazy-loading');
            obs.observe(element);
        }
    });
    
    return obs;
}

export function observeLazyElement(element, options = {}) {
    const obs = createObserver(options);
    element.classList.add('lazy-loading');
    obs.observe(element);
    return obs;
}

export function unobserveLazyElement(element) {
    if (observer) {
        observer.unobserve(element);
    }
}

export function destroyLazyLoading() {
    if (observer) {
        observer.disconnect();
        observer = null;
    }
    preloadQueue = [];
    isProcessingQueue = false;
}

export function createLazyImage(src, alt = '', options = {}) {
    const img = document.createElement('img');
    img.dataset.src = src;
    img.alt = alt;
    img.classList.add('lazy-loading');
    
    if (options.className) {
        img.classList.add(options.className);
    }
    
    if (options.placeholder) {
        img.src = options.placeholder;
    }
    
    if (options.priority) {
        img.dataset.priority = options.priority;
    }
    
    if (options.fallback) {
        img.dataset.fallback = options.fallback;
    }
    
    observeLazyElement(img);
    
    return img;
}

export function createLazyBackgroundImage(src, options = {}) {
    const div = document.createElement('div');
    div.dataset.bgImage = `url('${src}')`;
    div.classList.add('lazy-loading');
    
    if (options.className) {
        div.classList.add(options.className);
    }
    
    if (options.priority) {
        div.dataset.priority = options.priority;
    }
    
    observeLazyElement(div);
    
    return div;
}

export function preloadImages(urls, options = {}) {
    const { concurrency = isMobile() ? 2 : 4, priority = 'low' } = options;
    
    return new Promise((resolve) => {
        const results = [];
        let index = 0;
        let active = 0;
        
        const loadNext = () => {
            while (active < concurrency && index < urls.length) {
                const url = urls[index++];
                active++;
                
                const img = new Image();
                img.onload = () => {
                    results.push({ url, success: true });
                    active--;
                    loadNext();
                };
                img.onerror = () => {
                    results.push({ url, success: false });
                    active--;
                    loadNext();
                };
                
                if (priority === 'low') {
                    requestIdleCallback(() => {
                        img.src = url;
                    }, { timeout: 100 });
                } else {
                    img.src = url;
                }
            }
            
            if (active === 0 && index >= urls.length) {
                resolve(results);
            }
        };
        
        loadNext();
    });
}

export function refreshLazyLoading() {
    if (observer) {
        const elements = document.querySelectorAll('.lazy-loading[data-src], .lazy-loading[data-bg-image]');
        elements.forEach(element => {
            observer.observe(element);
        });
    }
}

export function forceLoadAll() {
    const elements = document.querySelectorAll('.lazy-loading[data-src], .lazy-loading[data-bg-image]');
    elements.forEach(element => {
        loadImage(element);
        if (observer) {
            observer.unobserve(element);
        }
    });
}

export function getLazyLoadingStats() {
    const total = document.querySelectorAll('[data-src], [data-bg-image]').length;
    const loaded = document.querySelectorAll('.lazy-loaded').length;
    const pending = document.querySelectorAll('.lazy-loading').length;
    const failed = document.querySelectorAll('.lazy-error').length;
    
    return { total, loaded, pending, failed, queueLength: preloadQueue.length };
}

export { observer as lazyLoadObserver };
