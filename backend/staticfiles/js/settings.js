document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('settingsForm');
    const symbolsInput = document.getElementById('symbolsInput');
    const symbolTags = document.getElementById('symbolTags');
    const searchResults = document.getElementById('searchResults');
    const submitBtn = document.getElementById('submitBtn');
    const alertContainer = document.getElementById('formAlertContainer');

    let tags = [];
    let debounceTimer;

    // --- 核心標籤 (Tag) 邏輯 ---
    
    // 將標籤渲染至 UI 介面
    const renderTags = () => {
        if (tags.length === 0) {
            symbolTags.innerHTML = `<span class="text-muted small opacity-50 pt-1">${gettext('選取股票於此顯示...')}</span>`;
            return;
        }
        symbolTags.innerHTML = tags.map((sym, index) => 
            `<span class="badge-glass d-flex align-items-center gap-2" style="font-size: 0.8rem; padding: 0.25rem 0.6rem;">
                ${sym}
                <i class="ph ph-x-circle cursor-pointer" onclick="removeTag(${index})" style="font-size: 0.9rem; opacity: 0.7;"></i>
            </span>`
        ).join('');
    };

    // 刪除按鈕的全域輔助函式
    window.removeTag = (index) => {
        tags.splice(index, 1);
        renderTags();
    };

    // 輔助函式：新增標籤並重設 UI
    const addTag = (val) => {
        // 如果輸入值為 "2330 台積電"，僅取第一部分（代碼）
        const cleanVal = val.split(' ')[0].replace(/[^a-zA-Z0-9^.]/g, '').trim().toUpperCase();
        if (cleanVal && !tags.includes(cleanVal)) {
            tags.push(cleanVal);
            renderTags();
        }
        symbolsInput.value = '';
        searchResults.style.display = 'none';
        symbolsInput.focus();
    };

    // 將 addTag 暴露至全域，以便搜尋結果項目的 onclick 呼叫
    window.addTag = addTag;

    // --- 搜尋建議 (Search Suggestion) 邏輯 ---

    const performSearch = async (query) => {
        if (query.length < 1) {
            searchResults.style.display = 'none';
            return;
        }

        const target = document.getElementById('adapterType').value;

        try {
            const response = await api.fetch(`/proxy/search/?q=${encodeURIComponent(query)}&target=${target}`);
            if (response && response.length > 0) {
                searchResults.innerHTML = response.map(item => `
                    <div class="search-item" onclick="addTag('${item.symbol}')">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="ticker-name">${item.symbol}</span>
                            <span class="text-muted" style="font-size: 0.65rem;">${item.typeDisp}</span>
                        </div>
                        <div class="text-truncate small opacity-75">${item.shortname}</div>
                    </div>
                `).join('');
                searchResults.style.display = 'block';
            } else {
                searchResults.style.display = 'none';
            }
        } catch (err) {
            console.error('Search failed', err);
        }
    };

    // --- 事件監聽器 (Event Listeners) ---

    symbolsInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();
        debounceTimer = setTimeout(() => performSearch(query), 200);
    });

    // 當市場目標 (適配器) 變更時重設搜尋
    document.getElementById('adapterType').addEventListener('change', () => {
        symbolsInput.value = '';
        searchResults.style.display = 'none';
        searchResults.innerHTML = '';
        tags = []; // Also switch context
        renderTags();
    });

    symbolsInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (symbolsInput.value) {
                addTag(symbolsInput.value);
            }
        }
    });

    // 點擊外部時關閉搜尋結果
    document.addEventListener('click', (e) => {
        if (!symbolsInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });

    // 排程開關連動邏輯
    const isActiveToggle = document.getElementById('isActive');
    const scheduleTimeInput = document.getElementById('scheduleTime');
    
    isActiveToggle.addEventListener('change', (e) => {
        if (e.target.checked) {
            scheduleTimeInput.disabled = false;
        } else {
            scheduleTimeInput.disabled = true;
            scheduleTimeInput.value = ''; // 清除輸入的時間
        }
    });

    // 表單警告工具
    const showAlert = (message, type = 'danger') => {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = [
            `<div class="alert alert-${type} alert-dismissible glass-card border-0 py-3" role="alert" style="color: #fff; background: ${type === 'danger' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)'}">`,
            `   <div>${message}</div>`,
            '   <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert" aria-label="Close"></button>',
            '</div>'
        ].join('');
        alertContainer.append(wrapper);
        setTimeout(() => wrapper.remove(), 5000);
    };

    // 表單提交邏輯
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (tags.length === 0 && symbolsInput.value) {
            addTag(symbolsInput.value);
        }

        if (tags.length === 0) {
            showAlert(gettext('請至少輸入一個股票代碼（代號）。'), 'danger');
            return;
        }

        const submitBtnOriginal = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="ph ph-spinner ph-spin"></i> ${gettext('儲存中...')}`;

        const scheduleTime = document.getElementById('scheduleTime').value;
        const payload = {
            name: document.getElementById('taskName').value,
            adapter_type: document.getElementById('adapterType').value,
            symbols: tags,
            is_active: document.getElementById('isActive').checked
        };
        
        if (scheduleTime) payload.schedule_time = scheduleTime + ":00";

        try {
            await api.fetch('/tasks/', {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            showAlert(gettext('任務已成功建立！'), 'success');
            setTimeout(() => window.location.href = '/', 1000);
        } catch (error) {
            const msg = error.data ? JSON.stringify(error.data) : gettext('儲存失敗，請檢查系統連線。');
            showAlert(msg, 'danger');
            submitBtn.disabled = false;
            submitBtn.innerHTML = submitBtnOriginal;
        }
    });
});
