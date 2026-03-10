/**
 * 触摸手势模块
 */

export function initTouchGestures(options = {}) {
    const {
        onSwipeRight,
        onSwipeLeft,
        onSwipeDown,
        onSwipeUp,
        threshold = 50,
        edgeThreshold = 30
    } = options;

    let touchStartX = 0;
    let touchStartY = 0;

    document.addEventListener('touchstart', (e) => {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
    }, { passive: true });

    document.addEventListener('touchend', (e) => {
        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        const diffX = touchEndX - touchStartX;
        const diffY = touchEndY - touchStartY;

        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > threshold) {
            if (diffX > 0 && touchStartX < edgeThreshold && onSwipeRight) {
                onSwipeRight();
            } else if (diffX < 0 && onSwipeLeft) {
                onSwipeLeft();
            }
        } else if (Math.abs(diffY) > Math.abs(diffX) && Math.abs(diffY) > threshold) {
            if (diffY > 0 && onSwipeDown) {
                onSwipeDown();
            } else if (diffY < 0 && onSwipeUp) {
                onSwipeUp();
            }
        }
    }, { passive: true });
}

export function initSwipeToClose(modalSelector, onClose, options = {}) {
    const { threshold = 100, maxDuration = 500 } = options;

    document.querySelectorAll(modalSelector).forEach(modal => {
        let touchStartY = 0;
        let touchStartTime = 0;
        let startScrollTop = 0;

        modal.addEventListener('touchstart', (e) => {
            touchStartY = e.touches[0].clientY;
            touchStartTime = Date.now();
            const scrollableContent = modal.querySelector('.filter-modal-body');
            startScrollTop = scrollableContent ? scrollableContent.scrollTop : 0;
        }, { passive: true });

        modal.addEventListener('touchend', (e) => {
            const touchEndY = e.changedTouches[0].clientY;
            const diffY = touchEndY - touchStartY;
            const touchDuration = Date.now() - touchStartTime;

            const scrollableContent = modal.querySelector('.filter-modal-body');
            const currentScrollTop = scrollableContent ? scrollableContent.scrollTop : 0;

            if (diffY > threshold && 
                touchDuration < maxDuration && 
                currentScrollTop === 0 && 
                startScrollTop === 0) {
                onClose();
            }
        }, { passive: true });
    });
}
