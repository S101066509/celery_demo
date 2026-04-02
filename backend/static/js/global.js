/**
 * 全域 UI 互動與系統健康輪詢
 * 管理時鐘、側邊欄以及背景狀態檢查。
 */

// 時鐘更新邏輯
function updateClock() {
    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour12: false });
    const clockEl = document.getElementById('clockDisplay');
    if (clockEl) clockEl.textContent = timeString;
}

// 目前連結高亮顯示 (Active Link Highlighting)
function highlightActiveLink() {
    const currentPath = window.location.pathname;
    const normalizedCurrent = currentPath.endsWith('/') ? currentPath : currentPath + '/';
    document.querySelectorAll('.sidebar-nav .nav-link').forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;
        const normalizedHref = href.endsWith('/') ? href : href + '/';
        if (normalizedHref === normalizedCurrent) {
            link.classList.add('active');
        }
    });
}

// 全域系統健康輪詢 (Global System Health Polling)
const updateSystemStatus = async () => {
    const indicator = document.querySelector('.status-indicator');
    if (!indicator) return;

    const dot = indicator.querySelector('.pulse-dot');
    const text = indicator.querySelector('.status-text');

    try {
        // 僅當資料庫、Redis 與 Celery 皆為 Online 時，API 才會回傳 200 OK
        await api.getHealth();

        if (dot) {
            dot.style.backgroundColor = 'var(--success)';
            dot.style.animation = 'pulse 2s infinite';
        }
        if (text) {
            text.textContent = gettext("系統已連線");
            text.style.color = 'var(--text-secondary)';
        }
    } catch (error) {
        if (dot) {
            dot.style.backgroundColor = 'var(--danger)';
            dot.style.animation = 'none';
        }

        let errorMsg = 'System Offline';
        if (error && error.data && error.data.components) {
            const comps = error.data.components;
            if (comps.database !== 'online') errorMsg = 'DB Error';
            else if (comps.redis !== 'online') errorMsg = 'Redis Error';
            else if (comps.celery !== 'online') errorMsg = 'Celery Error';
        }

        if (text) {
            text.textContent = errorMsg;
            text.style.color = 'var(--danger)';
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // 初始呼叫
    updateClock();
    highlightActiveLink();
    updateSystemStatus();

    // 定時任務 (Intervals)
    setInterval(updateClock, 1000);
    setInterval(updateSystemStatus, 10000);
});
