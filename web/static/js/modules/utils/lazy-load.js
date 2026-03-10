/**
 * 图片懒加载模块
 * 
 * 使用 Intersection Observer API 实现高性能图片懒加载
 */

let observer = null;

const defaultOptions = {
    rootMargin: '100px',
    threshold: 0.1
};

function createObserver(options = {}) {
    if (observer) {
        return observer;
    }
    
    const config = { ...defaultOptions, ...options };
    
    observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                loadImage(element);
                observer.unobserve(element);
            }
        });
    }, config);
    
    return observer;
}

function loadImage(element) {
    if (element.tagName === 'IMG') {
        const src = element.dataset.src;
        const srcset = element.dataset.srcset;
        
        if (src) {
            element.src = src;
            element.removeAttribute('data-src');
        }
        
        if (srcset) {
            element.srcset = srcset;
            element.removeAttribute('data-srcset');
        }
        
        element.classList.add('lazy-loaded');
        element.classList.remove('lazy-loading');
    } else if (element.dataset.bgImage) {
        element.style.backgroundImage = element.dataset.bgImage;
        element.removeAttribute('data-bg-image');
        element.classList.add('lazy-loaded');
        element.classList.remove('lazy-loading');
    }
}

export function setupLazyLoading(selector = 'img[data-src], [data-bg-image]', options = {}) {
    const obs = createObserver(options);
    
    const elements = document.querySelectorAll(selector);
    elements.forEach(element => {
        element.classList.add('lazy-loading');
        obs.observe(element);
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
    
    observeLazyElement(div);
    
    return div;
}

export function preloadImages(urls) {
    return Promise.all(
        urls.map(url => {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => resolve(url);
                img.onerror = () => reject(url);
                img.src = url;
            });
        })
    );
}

export { observer as lazyLoadObserver };
