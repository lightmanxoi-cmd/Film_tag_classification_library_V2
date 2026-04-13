/**
 * API 请求模块
 * 
 * 封装 fetch 请求，提供统一的认证处理和错误处理
 * 
 * 支持的服务端错误码：
 * - UNAUTHORIZED: 未登录
 * - SESSION_ABSOLUTE_TIMEOUT: 会话绝对超时（24小时）
 * - SESSION_INACTIVITY_TIMEOUT: 会话空闲超时（2小时）
 */

const AUTH_ERROR_EVENT = 'auth-error';

function dispatchAuthError(data) {
    window.dispatchEvent(new CustomEvent(AUTH_ERROR_EVENT, { detail: data }));
}

function getTimeoutMessage(errorCode) {
    switch (errorCode) {
        case 'SESSION_ABSOLUTE_TIMEOUT':
            return '会话已过期，请重新登录';
        case 'SESSION_INACTIVITY_TIMEOUT':
            return '长时间未操作，请重新登录';
        default:
            return '未授权访问，请先登录';
    }
}

export async function fetchWithAuth(url, options = {}) {
    const response = await fetch(url, options);
    
    if (response.status === 401) {
        const data = await response.clone().json().catch(() => ({}));
        const errorCode = data.error_code || 'UNAUTHORIZED';
        const message = data.error || getTimeoutMessage(errorCode);
        
        dispatchAuthError({ ...data, errorCode, message });
        
        alert(message);
        window.location.href = '/login';
        throw new Error(message);
    }
    
    return response;
}

export async function fetchJSON(url, options = {}) {
    const response = await fetchWithAuth(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    });
    return response.json();
}

export async function postJSON(url, data, options = {}) {
    return fetchJSON(url, {
        ...options,
        method: 'POST',
        body: JSON.stringify(data)
    });
}

export { AUTH_ERROR_EVENT };
