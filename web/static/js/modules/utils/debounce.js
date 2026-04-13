export function debounce(fn, delay = 300) {
    let timer = null;
    return function (...args) {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => {
            fn.apply(this, args);
            timer = null;
        }, delay);
    };
}

export function throttle(fn, interval = 500) {
    let lastTime = 0;
    let timer = null;
    return function (...args) {
        const now = Date.now();
        const remaining = interval - (now - lastTime);

        if (remaining <= 0) {
            if (timer) {
                clearTimeout(timer);
                timer = null;
            }
            lastTime = now;
            fn.apply(this, args);
        } else if (!timer) {
            timer = setTimeout(() => {
                lastTime = Date.now();
                timer = null;
                fn.apply(this, args);
            }, remaining);
        }
    };
}

export function withLoading(fn, btnId) {
    let pending = false;
    return async function (...args) {
        if (pending) return;
        const btn = btnId ? document.getElementById(btnId) : null;
        if (btn && btn.disabled) return;

        pending = true;
        if (btn) {
            btn.disabled = true;
            btn.dataset.originalText = btn.textContent;
            btn.textContent = '处理中...';
        }

        try {
            return await fn.apply(this, args);
        } finally {
            pending = false;
            if (btn) {
                btn.disabled = false;
                btn.textContent = btn.dataset.originalText || btn.textContent;
                delete btn.dataset.originalText;
            }
        }
    };
}
