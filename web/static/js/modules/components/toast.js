/**
 * Toast 提示组件
 */

let toastContainer = null;

function ensureContainer() {
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.cssText = `
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 3000;
            display: flex;
            flex-direction: column;
            gap: 8px;
            pointer-events: none;
        `;
        document.body.appendChild(toastContainer);
    }
    return toastContainer;
}

export function showToast(message, type = 'info', duration = 3000) {
    const container = ensureContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const bgColors = {
        info: 'rgba(229, 9, 20, 0.9)',
        success: 'rgba(46, 125, 50, 0.9)',
        warning: 'rgba(255, 152, 0, 0.9)',
        error: 'rgba(244, 67, 54, 0.9)'
    };
    
    toast.style.cssText = `
        background: ${bgColors[type] || bgColors.info};
        color: #fff;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 14px;
        max-width: 90%;
        text-align: center;
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.3s ease;
        pointer-events: auto;
    `;
    
    toast.textContent = message;
    container.appendChild(toast);
    
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, duration);
}

export function showSuccess(message) {
    showToast(message, 'success');
}

export function showWarning(message) {
    showToast(message, 'warning');
}

export function showError(message) {
    showToast(message, 'error');
}
