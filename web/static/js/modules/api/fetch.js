/**
 * API 请求模块
 * 
 * 封装 fetch 请求，提供统一的认证处理和错误处理
 */

const AUTH_ERROR_EVENT = 'auth-error';

function dispatchAuthError(data) {
    window.dispatchEvent(new CustomEvent(AUTH_ERROR_EVENT, { detail: data }));
}

export async function fetchWithAuth(url, options = {}) {
    const response = await fetch(url, options);
    
    if (response.status === 401) {
        const data = await response.clone().json().catch(() => ({}));
        dispatchAuthError(data);
        if (data.timeout) {
            alert('登录已过期，请重新登录');
        }
        window.location.href = '/login';
        throw new Error('Unauthorized');
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
