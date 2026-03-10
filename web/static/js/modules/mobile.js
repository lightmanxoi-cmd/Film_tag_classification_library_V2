/**
 * 移动端交互优化模块
 * 
 * 提供触摸手势、下拉刷新、快速滚动等移动端专属功能
 */

class MobileOptimizer {
    constructor(options = {}) {
        this.options = {
            enablePullToRefresh: true,
            enableFastScroll: true,
            enableHapticFeedback: true,
            enableSwipeNavigation: true,
            ...options
        };
        
        this.isMobile = this._detectMobile();
        this.isTouch = 'ontouchstart' in window;
        this.isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        this.isAndroid = /Android/.test(navigator.userAgent);
        
        this._pullToRefreshState = {
            startY: 0,
            pulling: false,
            threshold: 80
        };
        
        this._scrollState = {
            lastScrollTop: 0,
            scrollDirection: 'down',
            isScrolling: false,
            scrollTimeout: null
        };
        
        this.init();
    }
    
    _detectMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) 
            || window.innerWidth < 1024;
    }
    
    init() {
        if (!this.isMobile && !this.isTouch) return;
        
        this._initViewportHeight();
        this._initTouchFeedback();
        this._initPullToRefresh();
        this._initFastScroll();
        this._initSwipeNavigation();
        this._initSafeArea();
        this._initOrientationChange();
        this._initScrollDetection();
        
        console.log('[MobileOptimizer] 移动端优化已启用');
    }
    
    _initViewportHeight() {
        const setVH = () => {
            const vh = window.innerHeight * 0.01;
            document.documentElement.style.setProperty('--vh', `${vh}px`);
        };
        
        setVH();
        window.addEventListener('resize', () => {
            requestAnimationFrame(setVH);
        });
        
        if (this.isIOS) {
            window.addEventListener('orientationchange', () => {
                setTimeout(setVH, 100);
            });
        }
    }
    
    _initTouchFeedback() {
        if (!this.options.enableHapticFeedback) return;
        
        document.addEventListener('touchstart', (e) => {
            const target = e.target.closest('button, .video-card, .tag-child, .tag-parent, .filter-tag-item');
            if (target) {
                target.classList.add('touch-active');
            }
        }, { passive: true });
        
        document.addEventListener('touchend', (e) => {
            const target = e.target.closest('button, .video-card, .tag-child, .tag-parent, .filter-tag-item');
            if (target) {
                setTimeout(() => {
                    target.classList.remove('touch-active');
                }, 150);
            }
        }, { passive: true });
        
        document.addEventListener('touchcancel', (e) => {
            const activeElements = document.querySelectorAll('.touch-active');
            activeElements.forEach(el => el.classList.remove('touch-active'));
        }, { passive: true });
    }
    
    _initPullToRefresh() {
        if (!this.options.enablePullToRefresh) return;
        
        const content = document.querySelector('.content');
        if (!content) return;
        
        let pullIndicator = document.querySelector('.pull-to-refresh');
        if (!pullIndicator) {
            pullIndicator = document.createElement('div');
            pullIndicator.className = 'pull-to-refresh';
            pullIndicator.innerHTML = '<div class="pull-to-refresh-icon"></div>';
            document.body.appendChild(pullIndicator);
        }
        
        let startY = 0;
        let pulling = false;
        let refreshing = false;
        const threshold = 80;
        
        content.addEventListener('touchstart', (e) => {
            if (content.scrollTop === 0 && !refreshing) {
                startY = e.touches[0].clientY;
                pulling = true;
            }
        }, { passive: true });
        
        content.addEventListener('touchmove', (e) => {
            if (!pulling || refreshing) return;
            
            const currentY = e.touches[0].clientY;
            const diff = currentY - startY;
            
            if (diff > 0 && content.scrollTop === 0) {
                const progress = Math.min(diff / threshold, 1);
                pullIndicator.style.transform = `translateY(${Math.min(diff * 0.5, 40)}px)`;
                pullIndicator.style.opacity = progress;
                
                if (diff > threshold) {
                    pullIndicator.classList.add('ready');
                } else {
                    pullIndicator.classList.remove('ready');
                }
            }
        }, { passive: true });
        
        content.addEventListener('touchend', (e) => {
            if (!pulling || refreshing) return;
            
            const currentY = e.changedTouches[0].clientY;
            const diff = currentY - startY;
            
            if (diff > threshold && content.scrollTop === 0) {
                refreshing = true;
                pullIndicator.classList.add('visible', 'refreshing');
                
                if (typeof this.options.onRefresh === 'function') {
                    Promise.resolve(this.options.onRefresh())
                        .finally(() => {
                            setTimeout(() => {
                                pullIndicator.classList.remove('visible', 'refreshing', 'ready');
                                pullIndicator.style.transform = '';
                                pullIndicator.style.opacity = '';
                                refreshing = false;
                            }, 300);
                        });
                } else if (typeof loadVideos === 'function') {
                    loadVideos(1);
                    setTimeout(() => {
                        pullIndicator.classList.remove('visible', 'refreshing', 'ready');
                        pullIndicator.style.transform = '';
                        pullIndicator.style.opacity = '';
                        refreshing = false;
                    }, 500);
                }
            } else {
                pullIndicator.classList.remove('visible', 'ready');
                pullIndicator.style.transform = '';
                pullIndicator.style.opacity = '';
            }
            
            pulling = false;
        }, { passive: true });
    }
    
    _initFastScroll() {
        if (!this.options.enableFastScroll) return;
        
        const sidebar = document.querySelector('.sidebar');
        const filterModal = document.querySelector('.filter-modal-body');
        
        [sidebar, filterModal].forEach(container => {
            if (!container) return;
            
            let scrollTimeout;
            let isScrollingFast = false;
            
            container.addEventListener('scroll', () => {
                if (!isScrollingFast) {
                    container.classList.add('fast-scroll');
                    isScrollingFast = true;
                }
                
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    container.classList.remove('fast-scroll');
                    isScrollingFast = false;
                }, 150);
            }, { passive: true });
        });
    }
    
    _initSwipeNavigation() {
        if (!this.options.enableSwipeNavigation) return;
        
        let touchStartX = 0;
        let touchStartY = 0;
        let isSwiping = false;
        const edgeThreshold = 30;
        const swipeThreshold = 80;
        
        document.addEventListener('touchstart', (e) => {
            if (e.touches.length === 1) {
                touchStartX = e.touches[0].clientX;
                touchStartY = e.touches[0].clientY;
                isSwiping = true;
            }
        }, { passive: true });
        
        document.addEventListener('touchend', (e) => {
            if (!isSwiping || e.changedTouches.length !== 1) return;
            
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;
            const diffX = touchEndX - touchStartX;
            const diffY = touchEndY - touchStartY;
            
            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > swipeThreshold) {
                const sidebar = document.getElementById('sidebar');
                const isOpen = sidebar && sidebar.classList.contains('open');
                
                if (diffX > 0 && !isOpen && touchStartX < edgeThreshold) {
                    if (typeof openMobileSidebar === 'function') {
                        openMobileSidebar();
                        this._hapticFeedback('light');
                    }
                } else if (diffX < 0 && isOpen) {
                    if (typeof closeMobileSidebar === 'function') {
                        closeMobileSidebar();
                        this._hapticFeedback('light');
                    }
                }
            }
            
            isSwiping = false;
        }, { passive: true });
    }
    
    _initSafeArea() {
        const updateSafeArea = () => {
            const safeAreaTop = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--sat') || '0');
            const safeAreaBottom = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--sab') || '0');
            
            document.documentElement.style.setProperty('--safe-area-top', `${safeAreaTop}px`);
            document.documentElement.style.setProperty('--safe-area-bottom', `${safeAreaBottom}px`);
        };
        
        updateSafeArea();
        window.addEventListener('resize', updateSafeArea);
    }
    
    _initOrientationChange() {
        let lastOrientation = window.orientation;
        
        const handleOrientationChange = () => {
            const currentOrientation = window.orientation;
            
            if (lastOrientation !== currentOrientation) {
                lastOrientation = currentOrientation;
                
                setTimeout(() => {
                    this._initViewportHeight();
                    
                    if (typeof this.options.onOrientationChange === 'function') {
                        this.options.onOrientationChange(currentOrientation);
                    }
                }, 100);
            }
        };
        
        window.addEventListener('orientationchange', handleOrientationChange);
        window.addEventListener('resize', handleOrientationChange);
    }
    
    _initScrollDetection() {
        const content = document.querySelector('.content');
        if (!content) return;
        
        let scrollTimeout;
        let lastScrollTop = 0;
        let ticking = false;
        
        const updateScrollState = () => {
            const scrollTop = content.scrollTop;
            const direction = scrollTop > lastScrollTop ? 'down' : 'up';
            
            if (direction !== this._scrollState.scrollDirection) {
                this._scrollState.scrollDirection = direction;
                
                if (typeof this.options.onScrollDirectionChange === 'function') {
                    this.options.onScrollDirectionChange(direction);
                }
            }
            
            this._scrollState.lastScrollTop = scrollTop;
            this._scrollState.isScrolling = true;
            
            clearTimeout(this._scrollState.scrollTimeout);
            this._scrollState.scrollTimeout = setTimeout(() => {
                this._scrollState.isScrolling = false;
            }, 150);
            
            ticking = false;
        };
        
        content.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(updateScrollState);
                ticking = true;
            }
        }, { passive: true });
    }
    
    _hapticFeedback(type = 'light') {
        if (!this.options.enableHapticFeedback) return;
        
        if ('vibrate' in navigator) {
            const patterns = {
                light: [10],
                medium: [20],
                heavy: [30],
                success: [10, 50, 10],
                error: [30, 50, 30]
            };
            
            navigator.vibrate(patterns[type] || patterns.light);
        }
    }
    
    isScrolling() {
        return this._scrollState.isScrolling;
    }
    
    getScrollDirection() {
        return this._scrollState.scrollDirection;
    }
    
    scrollToTop(smooth = true) {
        const content = document.querySelector('.content');
        if (content) {
            content.scrollTo({
                top: 0,
                behavior: smooth ? 'smooth' : 'auto'
            });
        }
    }
    
    showBottomBar() {
        const bottomBar = document.querySelector('.mobile-bottom-bar');
        if (bottomBar) {
            bottomBar.classList.add('visible');
        }
    }
    
    hideBottomBar() {
        const bottomBar = document.querySelector('.mobile-bottom-bar');
        if (bottomBar) {
            bottomBar.classList.remove('visible');
        }
    }
    
    showFAB() {
        const fab = document.querySelector('.mobile-fab');
        if (fab) {
            fab.classList.add('visible');
        }
    }
    
    hideFAB() {
        const fab = document.querySelector('.mobile-fab');
        if (fab) {
            fab.classList.remove('visible');
        }
    }
    
    showToast(message, duration = 2000) {
        let toast = document.querySelector('.toast');
        
        if (!toast) {
            toast = document.createElement('div');
            toast.className = 'toast';
            document.body.appendChild(toast);
        }
        
        toast.textContent = message;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, duration);
    }
    
    vibrate(pattern = 'light') {
        this._hapticFeedback(pattern);
    }
    
    destroy() {
        window.removeEventListener('resize', this._initViewportHeight);
        window.removeEventListener('orientationchange', this._initOrientationChange);
    }
}

class MobileVideoPlayer {
    constructor() {
        this.isFullscreen = false;
        this.controlsTimeout = null;
        this.init();
    }
    
    init() {
        this._initFullscreenToggle();
        this._initControlsAutoHide();
        this._initOrientationLock();
        this._initSwipeGestures();
    }
    
    _initFullscreenToggle() {
        document.addEventListener('fullscreenchange', () => {
            this.isFullscreen = !!document.fullscreenElement;
            const modal = document.querySelector('.video-player-modal');
            
            if (modal) {
                if (this.isFullscreen) {
                    modal.classList.add('is-fullscreen');
                    if (screen.orientation && screen.orientation.lock) {
                        screen.orientation.lock('landscape').catch(() => {});
                    }
                } else {
                    modal.classList.remove('is-fullscreen');
                    if (screen.orientation && screen.orientation.unlock) {
                        screen.orientation.unlock();
                    }
                }
            }
        });
    }
    
    _initControlsAutoHide() {
        const modal = document.querySelector('.video-player-modal');
        if (!modal) return;
        
        const showControls = () => {
            modal.classList.add('show-controls');
            clearTimeout(this.controlsTimeout);
            
            this.controlsTimeout = setTimeout(() => {
                if (!modal.matches(':hover')) {
                    modal.classList.remove('show-controls');
                }
            }, 3000);
        };
        
        modal.addEventListener('touchstart', showControls, { passive: true });
        modal.addEventListener('touchmove', showControls, { passive: true });
    }
    
    _initOrientationLock() {
        if (!('orientation' in screen)) return;
        
        const modal = document.querySelector('.video-player-modal');
        if (!modal) return;
        
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class') {
                    const isOpen = modal.classList.contains('show');
                    
                    if (isOpen && this.isFullscreen) {
                        if (screen.orientation.lock) {
                            screen.orientation.lock('landscape').catch(() => {});
                        }
                    }
                }
            });
        });
        
        observer.observe(modal, { attributes: true });
    }
    
    _initSwipeGestures() {
        const modal = document.querySelector('.video-player-modal');
        if (!modal) return;
        
        let touchStartY = 0;
        let touchStartTime = 0;
        
        modal.addEventListener('touchstart', (e) => {
            if (e.target.closest('.video-js, .vjs-control-bar, .video-info')) return;
            
            touchStartY = e.touches[0].clientY;
            touchStartTime = Date.now();
        }, { passive: true });
        
        modal.addEventListener('touchend', (e) => {
            if (e.target.closest('.video-js, .vjs-control-bar, .video-info')) return;
            
            const touchEndY = e.changedTouches[0].clientY;
            const diffY = touchEndY - touchStartY;
            const touchDuration = Date.now() - touchStartTime;
            
            if (diffY > 100 && touchDuration < 500) {
                if (typeof closeVideoModal === 'function') {
                    closeVideoModal();
                }
            }
        }, { passive: true });
    }
    
    requestFullscreen() {
        const player = document.getElementById('videoPlayer');
        if (player && player.requestFullscreen) {
            player.requestFullscreen();
        }
    }
    
    exitFullscreen() {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }
    
    toggleFullscreen() {
        if (this.isFullscreen) {
            this.exitFullscreen();
        } else {
            this.requestFullscreen();
        }
    }
}

class MobileLazyLoader {
    constructor(options = {}) {
        this.options = {
            rootMargin: '200px 0px',
            threshold: 0.1,
            fadeInDuration: 300,
            ...options
        };
        
        this.observer = null;
        this.init();
    }
    
    init() {
        if (!('IntersectionObserver' in window)) {
            this._loadAllImages();
            return;
        }
        
        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this._loadImage(entry.target);
                    this.observer.unobserve(entry.target);
                }
            });
        }, {
            rootMargin: this.options.rootMargin,
            threshold: this.options.threshold
        });
        
        this._observeImages();
    }
    
    _observeImages() {
        const images = document.querySelectorAll('.lazy-loading[data-src], .lazy-loading[data-bg-image]');
        images.forEach(img => this.observer.observe(img));
    }
    
    _loadImage(element) {
        const src = element.dataset.src;
        const bgImage = element.dataset.bgImage;
        
        if (src) {
            const img = new Image();
            img.onload = () => {
                if (element.tagName === 'IMG') {
                    element.src = src;
                }
                element.classList.remove('lazy-loading');
                element.classList.add('lazy-loaded');
                delete element.dataset.src;
            };
            img.onerror = () => {
                element.classList.remove('lazy-loading');
                element.classList.add('lazy-error');
            };
            img.src = src;
        }
        
        if (bgImage) {
            const img = new Image();
            img.onload = () => {
                element.style.backgroundImage = bgImage;
                element.classList.remove('lazy-loading');
                element.classList.add('lazy-loaded');
                delete element.dataset.bgImage;
            };
            img.onerror = () => {
                element.classList.remove('lazy-loading');
                element.classList.add('lazy-error');
            };
            img.src = bgImage.match(/url\('([^']+)'\)/)?.[1] || bgImage;
        }
    }
    
    _loadAllImages() {
        const images = document.querySelectorAll('.lazy-loading[data-src], .lazy-loading[data-bg-image]');
        images.forEach(img => this._loadImage(img));
    }
    
    refresh() {
        this._observeImages();
    }
    
    destroy() {
        if (this.observer) {
            this.observer.disconnect();
        }
    }
}

class MobileScrollToTop {
    constructor(options = {}) {
        this.options = {
            threshold: 300,
            ...options
        };
        
        this.button = null;
        this.init();
    }
    
    init() {
        this._createButton();
        this._bindEvents();
    }
    
    _createButton() {
        this.button = document.createElement('button');
        this.button.className = 'scroll-to-top-btn';
        this.button.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                <path d="M7.41 15.41L12 10.83l4.59 4.58L18 14l-6-6-6 6z"/>
            </svg>
        `;
        this.button.style.cssText = `
            position: fixed;
            bottom: calc(80px + env(safe-area-inset-bottom, 0px));
            right: 16px;
            width: 48px;
            height: 48px;
            background: rgba(229, 9, 20, 0.9);
            border: none;
            border-radius: 50%;
            color: #fff;
            cursor: pointer;
            z-index: 901;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transform: scale(0.8);
            transition: all 0.3s ease;
            pointer-events: none;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        `;
        
        this.button.addEventListener('click', () => {
            const content = document.querySelector('.content');
            if (content) {
                content.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            }
        });
        
        document.body.appendChild(this.button);
    }
    
    _bindEvents() {
        const content = document.querySelector('.content');
        if (!content) return;
        
        let ticking = false;
        
        content.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    this._updateVisibility(content.scrollTop);
                    ticking = false;
                });
                ticking = true;
            }
        }, { passive: true });
    }
    
    _updateVisibility(scrollTop) {
        if (scrollTop > this.options.threshold) {
            this.button.style.opacity = '1';
            this.button.style.transform = 'scale(1)';
            this.button.style.pointerEvents = 'auto';
        } else {
            this.button.style.opacity = '0';
            this.button.style.transform = 'scale(0.8)';
            this.button.style.pointerEvents = 'none';
        }
    }
    
    show() {
        this.button.style.opacity = '1';
        this.button.style.transform = 'scale(1)';
        this.button.style.pointerEvents = 'auto';
    }
    
    hide() {
        this.button.style.opacity = '0';
        this.button.style.transform = 'scale(0.8)';
        this.button.style.pointerEvents = 'none';
    }
}

let mobileOptimizer = null;
let mobileVideoPlayer = null;
let mobileLazyLoader = null;
let mobileScrollToTop = null;

function initMobileOptimizations(options = {}) {
    mobileOptimizer = new MobileOptimizer(options);
    mobileVideoPlayer = new MobileVideoPlayer();
    mobileLazyLoader = new MobileLazyLoader();
    mobileScrollToTop = new MobileScrollToTop();
    
    window.mobileOptimizer = mobileOptimizer;
    window.mobileVideoPlayer = mobileVideoPlayer;
    window.mobileLazyLoader = mobileLazyLoader;
    window.mobileScrollToTop = mobileScrollToTop;
    
    return {
        optimizer: mobileOptimizer,
        videoPlayer: mobileVideoPlayer,
        lazyLoader: mobileLazyLoader,
        scrollToTop: mobileScrollToTop
    };
}

function getMobileOptimizer() {
    return mobileOptimizer;
}

function showToast(message, duration = 2000) {
    if (mobileOptimizer) {
        mobileOptimizer.showToast(message, duration);
    } else {
        alert(message);
    }
}

export {
    MobileOptimizer,
    MobileVideoPlayer,
    MobileLazyLoader,
    MobileScrollToTop,
    initMobileOptimizations,
    getMobileOptimizer,
    showToast
};
