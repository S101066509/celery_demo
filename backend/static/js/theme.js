/**
 * UI 主題管理邏輯
 * 處理深色/淺色模式的切換與持久化。
 */

const themeBtn = document.getElementById('themeToggle');
const themeIcon = document.getElementById('themeIcon');

const updateIcon = (theme) => {
    if (themeIcon) {
        themeIcon.className = theme === 'dark' ? 'ph ph-sun' : 'ph ph-moon-stars';
    }
};

const setTheme = (theme) => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    updateIcon(theme);
};

// 載入時同步圖示狀態 (主題已由 head 腳本設定)
document.addEventListener('DOMContentLoaded', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    updateIcon(currentTheme);

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const theme = document.documentElement.getAttribute('data-theme');
            const newTheme = theme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
        });
    }
});
