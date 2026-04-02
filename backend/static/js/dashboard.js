document.addEventListener('DOMContentLoaded', () => {
    const taskGrid = document.getElementById('taskGrid');
    let pollingInterval = null;

    // 輔助函式：將狀態映射到 CSS 類別與圖示
    const getStatusConfig = (status) => {
        const lower = (status || 'idle').toLowerCase();
        if (lower === 'success') return { class: 'badge-success', icon: 'ph-check-circle' };
        if (lower === 'failed') return { class: 'badge-danger', icon: 'ph-x-circle' };
        if (lower === 'running') return { class: 'badge-running', icon: 'ph-spinner ph-spin' };
        return { class: 'badge-idle', icon: 'ph-clock' };
    };

    // 輔助函式：格式化日期
    const formatDate = (dateStr) => {
        if (!dateStr) return gettext('從未執行');
        const d = new Date(dateStr);
        return d.toLocaleString(document.documentElement.lang === 'zh-hant' ? 'zh-TW' : 'en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute:'2-digit' });
    };

    // 渲染單個任務卡片，帶有交錯進入動畫 (Staggered Animation)
    const createCardHTML = (task, index) => {
        const statusConfig = getStatusConfig(task.status);
        const tagsHTML = task.symbols.map(sym => `<span class="badge-glass">${sym}</span>`).join(' ');

        const isRunning = task.status === 'RUNNING';
        const btnText = isRunning ? gettext('處理中...') : gettext('立即執行');
        const btnDisabled = isRunning ? 'disabled' : '';
        const delay = index * 80; // staggered entrance

        return `
            <div class="col-12 col-xl-4 col-lg-6 card-animated" style="animation-delay: ${delay}ms;">
                <div class="glass-card h-100 d-flex flex-column">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <h4 class="m-0" style="font-size: 1.2rem;">${task.name}</h4>
                        <span class="badge-glass ${statusConfig.class} d-flex align-items-center gap-1">
                            <i class="ph ${statusConfig.icon}"></i>
                            ${task.status}
                        </span>
                    </div>

                    <div class="mb-3">
                        <div class="info-row">
                            <span class="info-label">${gettext('來源適配器')}</span>
                            <span class="info-value">${task.adapter_type.toUpperCase()}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${gettext('排程時間')}</span>
                            <span class="info-value">${task.schedule_time || gettext('手動觸發')}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${gettext('最後執行')}</span>
                            <span class="info-value">${formatDate(task.last_run_at)}</span>
                        </div>
                    </div>

                    <div class="mb-4">
                        <div class="mb-2" style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); font-weight: 600;">${gettext('追蹤股票代號')}</div>
                        <div class="d-flex flex-wrap gap-2">
                            ${tagsHTML}
                        </div>
                    </div>

                    <div class="mt-auto pt-3 d-flex gap-2" style="border-top: 1px solid var(--border-glass)">
                        <button class="btn-gradient flex-grow-1 d-flex justify-content-center align-items-center gap-2 trigger-btn"
                                data-id="${task.id}" ${btnDisabled} style="height: 42px;">
                            <i class="ph ph-lightning"></i>
                            ${btnText}
                        </button>
                        <button class="btn btn-danger d-flex justify-content-center align-items-center p-0 delete-btn"
                                style="border-radius: 8px; width: 42px; height: 42px; flex-shrink: 0;" data-id="${task.id}">
                            <i class="ph ph-trash" style="font-size: 1.15rem;"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    };

    // 載入任務並渲染
    const loadTasks = async () => {
        try {
            const data = await api.getTasks();
            const tasks = data.results || data; // Handle paginated or flat
            
            if (tasks.length === 0) {
                taskGrid.innerHTML = `
                    <div class="col-12 glass-card empty-state">
                        <i class="ph ph-ghost"></i>
                        <h4>${gettext('目前尚未設定任何數據任務')}</h4>
                        <a href="/data/settings/" class="btn-gradient d-inline-block text-decoration-none">${gettext('建立您的第一個任務')}</a>
                    </div>
                `;
                return;
            }

            taskGrid.innerHTML = tasks.map((task, i) => createCardHTML(task, i)).join('');
            attachEventListeners();
        } catch (error) {
            console.error('Failed to load tasks', error);
            taskGrid.innerHTML = `<div class="col-12 text-danger">${gettext('載入工作清單失敗，請檢查網路連線。')}</div>`;
        }
    };

    const attachEventListeners = () => {
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if(!confirm(gettext('確定要刪除此任務嗎？此動作無法復原。'))) return;
                const taskId = e.currentTarget.getAttribute('data-id');
                const originalHtml = e.currentTarget.innerHTML;
                
                e.currentTarget.disabled = true;
                e.currentTarget.innerHTML = `<i class="ph ph-spinner ph-spin" style="font-size: 1.25rem;"></i>`;
                
                try {
                    await api.deleteTask(taskId);
                    showToast(gettext('已刪除'), gettext('數據任務已成功移除。'));
                    loadTasks();
                } catch (err) {
                    showToast(gettext('錯誤'), gettext('無法刪除任務，請稍後再試。'), true);
                    e.currentTarget.disabled = false;
                    e.currentTarget.innerHTML = originalHtml;
                }
            });
        });

        document.querySelectorAll('.trigger-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const taskId = e.currentTarget.getAttribute('data-id');
                const originalHtml = e.currentTarget.innerHTML;
                
                // 設定載入中狀態
                e.currentTarget.disabled = true;
                e.currentTarget.innerHTML = `<i class="ph ph-spinner ph-spin"></i> ${gettext('啟動中...')}`;
                
                try {
                    await api.triggerTask(taskId);
                    showToast(gettext('任務已發送'), `${gettext('任務編號')} #${taskId} ${gettext('已加入 Celery 工作隊列。')}`);
                    // 立即重新載入以顯示 "RUNNING"
                    setTimeout(loadTasks, 500); 
                } catch (err) {
                    const msg = err.data && err.data.error ? err.data.error : gettext('任務啟動失敗，請檢查系統狀態。');
                    showToast(gettext('連線錯誤'), msg, true);
                    e.currentTarget.disabled = false;
                    e.currentTarget.innerHTML = originalHtml;
                }
            });
        });
    };

    const showToast = (title, message, isError = false) => {
        const toastEl = document.getElementById('actionToast');
        document.getElementById('toastTitle').textContent = title;
        document.getElementById('toastTitle').style.color = isError ? 'var(--danger)' : 'var(--success)';
        document.getElementById('toastMessage').textContent = message;
        
        const icon = toastEl.querySelector('.toast-header i');
        icon.className = isError ? 'ph-fill ph-x-circle' : 'ph-fill ph-check-circle';
        icon.style.color = isError ? 'var(--danger)' : 'var(--success)';

        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    };

    // 初始載入
    loadTasks();

    // 開始每 10 秒進行一次輪詢 (Polling)，以獲取即時狀態更新
    pollingInterval = setInterval(loadTasks, 10000);
});
