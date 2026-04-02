/**
 * API 處理類別，用於與 Django REST API 進行通訊。
 * 使用 ES6 Classes 與 Fetch API。
 */
class ApiHandler {
    constructor(baseUrl = '/api/v1') {
        this.baseUrl = baseUrl;
    }

    // 通用的 fetch 方法
    async fetch(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        // 取得 CSRF token 用於變更操作 (Mutation: POST, PUT, PATCH, DELETE)
        const csrfTokenMatch = document.cookie.match(/csrftoken=([^;]+)/);
        const csrfToken = csrfTokenMatch ? csrfTokenMatch[1] : null;

        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...options.headers
        };

        // 如果不是 GET 請求且有 token，則加入 X-CSRFToken
        const method = (options.method || 'GET').toUpperCase();
        if (method !== 'GET' && csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json().catch(() => ({}));
            
            if (!response.ok) {
                throw { status: response.status, data };
            }
            
            return data;
        } catch (error) {
            console.error(`API Error on ${url}:`, error);
            throw error;
        }
    }

    // 任務相關端點 (Task endpoints)
    async getTasks() {
        return this.fetch('/tasks/');
    }

    async triggerTask(id) {
        return this.fetch(`/tasks/${id}/executions/`, { method: 'POST' });
    }

    async deleteTask(id) {
        return this.fetch(`/tasks/${id}/`, { method: 'DELETE' });
    }

    // 股價相關端點 (Price endpoints)
    async getPrices(params = '') {
        return this.fetch(`/prices/${params}`);
    }

    // 系統健康檢查端點 (System Health endpoint)
    async getHealth() {
        return this.fetch('/health/');
    }

    // 錯誤日誌端點 (Error Logs endpoint)
    async getErrors(params = '') {
        return this.fetch(`/errors/${params}`);
    }
}

// 全域實例 (Global instance)
const api = new ApiHandler();
