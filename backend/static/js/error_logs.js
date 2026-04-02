document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('errorTableBody');
    const levelFilter = document.getElementById('levelFilter');
    const refreshBtn = document.getElementById('refreshErrorsBtn');

    // 格式化日期
    const formatDate = (dateStr) => {
        if (!dateStr) return '--';
        const d = new Date(dateStr);
        const lang = document.documentElement.lang === 'zh-hant' ? 'zh-TW' : 'en-US';
        return d.toLocaleString(lang, {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    };

    // 獲取錯誤等級對應的 CSS 類別
    const getLevelClass = (level) => {
        const l = (level || '').toLowerCase();
        if (l === 'critical') return 'badge-level-critical';
        if (l === 'warning') return 'badge-level-warning';
        return 'badge-level-error';
    };

    // 切換 Traceback 的顯示狀態
    const toggleTraceback = (rowId) => {
        const tbRow = document.getElementById(`tb-${rowId}`);
        if (tbRow) {
            tbRow.style.display = tbRow.style.display === 'none' ? 'table-row' : 'none';
        }
    };
    window.toggleTraceback = toggleTraceback;

    // 載入並渲染錯誤記錄
    const loadErrors = async () => {
        const level = levelFilter.value;
        const params = level ? `?level=${level}` : '';

        try {
            const data = await api.getErrors(params);
            const errors = data.results || data;

            if (errors.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center py-5">
                            <i class="ph ph-shield-check" style="font-size: 3rem; color: var(--success); opacity: 0.6;"></i>
                            <p class="mt-3" style="color: var(--text-muted);">${gettext('目前沒有錯誤記錄，系統運行正常。')}</p>
                        </td>
                    </tr>
                `;
                return;
            }

            tableBody.innerHTML = errors.map((err, idx) => {
                const hasTrace = err.traceback && err.traceback.trim().length > 0;
                const expandIcon = hasTrace ? '<i class="ph ph-caret-down" style="font-size: 0.75rem; opacity: 0.5;"></i>' : '';

                return `
                    <tr onclick="${hasTrace ? `toggleTraceback(${err.id})` : ''}" title="${hasTrace ? gettext('點擊展開 Traceback') : ''}">
                        <td style="white-space: nowrap;">${formatDate(err.created_at)}</td>
                        <td><span class="badge-level ${getLevelClass(err.level)}">${err.level}</span></td>
                        <td style="font-family: 'SF Mono', monospace; font-size: 0.8rem; color: var(--text-muted);">${err.source}</td>
                        <td>${err.task_name || '<span style="opacity:0.4">—</span>'}</td>
                        <td class="msg-cell">${err.message} ${expandIcon}</td>
                    </tr>
                    ${hasTrace ? `<tr id="tb-${err.id}" class="traceback-row" style="display: none;">
                        <td colspan="5"><div class="traceback-content">${err.traceback}</div></td>
                    </tr>` : ''}
                `;
            }).join('');

        } catch (error) {
            console.error('Failed to load error logs', error);
            tableBody.innerHTML = `<tr><td colspan="5" class="text-danger text-center py-4">${gettext('載入錯誤記錄失敗。')}</td></tr>`;
        }
    };

    // 事件監聽器 (Event listeners)
    levelFilter.addEventListener('change', loadErrors);
    refreshBtn.addEventListener('click', loadErrors);

    // 初始載入
    loadErrors();

    // 每一分鐘進行一次自動刷新
    setInterval(loadErrors, 60000);
});
