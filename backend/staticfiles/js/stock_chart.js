document.addEventListener('DOMContentLoaded', () => {
    const taskSelect = document.getElementById('taskSelect');
    const refreshBtn = document.getElementById('refreshChartBtn');
    const togglesContainer = document.getElementById('stockToggles');
    const ctx = document.getElementById('priceChart').getContext('2d');
    
    let currentChart = null;
    let currentTasks = [];
    let selectedTaskData = {}; // 快取：{ symbol: [...dataRecords] }
    let activeSymbols = new Set();
    
    // 用於不同股票線條的現代化顏色配色
    const colors = [
        { border: '#a855f7', point: '#22d3ee' }, // Purple / Cyan
        { border: '#22d3ee', point: '#a855f7' }, // Cyan / Purple
        { border: '#f43f5e', point: '#fecdd3' }, // Rose
        { border: '#10b981', point: '#a7f3d0' }, // Emerald
        { border: '#f59e0b', point: '#fde68a' }, // Amber
        { border: '#3b82f6', point: '#bfdbfe' }, // Blue
        { border: '#ec4899', point: '#fbcfe8' }, // Pink
    ];

    // 載入可用的任務
    const initSelectOptions = async () => {
        try {
            const data = await api.getTasks();
            currentTasks = data.results || data;
            
            if (currentTasks.length > 0) {
                taskSelect.innerHTML = currentTasks.map(t => 
                    `<option value="${t.id}">${t.name} (${t.symbols.length} ${gettext('檔')})</option>`
                ).join('');
                
                // 觸發首次載入
                loadTaskData(taskSelect.value);
            } else {
                taskSelect.innerHTML = `<option value="">${gettext('No tasks found')}</option>`;
            }
        } catch (error) {
            console.error(error);
            taskSelect.innerHTML = `<option value="">${gettext('無法載入任務')}</option>`;
        }
    };

    const loadTaskData = async (taskId) => {
        if (!taskId) return;
        const task = currentTasks.find(t => t.id.toString() === taskId);
        if (!task || !task.symbols) return;
        
        togglesContainer.innerHTML = `<span class="text-muted" style="font-size: 0.85rem;"><i class="ph ph-spinner-gap ph-spin"></i> ${gettext('載入數據中...')}</span>`;
        selectedTaskData = {};
        
        try {
            // 同時抓取該任務內的所有股票代碼數據
            await Promise.all(task.symbols.map(async (sym) => {
                const data = await api.getPrices(`?ticker=${sym}`);
                selectedTaskData[sym] = data.results || data;
            }));
            
            // 預設情況下，初始開啟所有股票顯示
            activeSymbols = new Set(task.symbols);
            
            renderToggles(task.symbols);
            updateView();
            
        } catch (error) {
            console.error('Failed to load prices for task symbols', error);
            togglesContainer.innerHTML = `<span class="text-danger">${gettext('載入失敗')}</span>`;
        }
    };

    const renderToggles = (symbols) => {
        togglesContainer.innerHTML = '';
        symbols.forEach((sym, idx) => {
            const btn = document.createElement('button');
            const colorObj = colors[idx % colors.length];
            // 設定樣式
            btn.className = 'btn btn-sm rounded-pill border-0 px-3 fw-bold';
            btn.style.transition = 'all 0.2s';
            
            const updateBtnStyle = () => {
                if (activeSymbols.has(sym)) {
                    btn.style.backgroundColor = `${colorObj.border}22`; // 22 is hex opacity
                    btn.style.color = colorObj.border;
                    btn.style.boxShadow = `0 0 10px ${colorObj.border}40`;
                } else {
                    btn.style.backgroundColor = 'rgba(255,255,255,0.05)';
                    btn.style.color = 'var(--text-muted)';
                    btn.style.boxShadow = 'none';
                }
            };
            
            btn.textContent = sym;
            updateBtnStyle();
            
            btn.addEventListener('click', () => {
                if (activeSymbols.has(sym)) {
                    activeSymbols.delete(sym);
                } else {
                    activeSymbols.add(sym);
                }
                updateBtnStyle();
                updateView(); // 重新渲染圖表與 KPI
            });
            
            togglesContainer.appendChild(btn);
        });
    };

    const updateView = () => {
        plotChart();
        updateKPI();
    };

    // 根據 *第一個* 活動中的股票代碼填滿 KPI 統計卡片
    const updateKPI = () => {
        const closeEl = document.getElementById('kpiClose');
        const highEl = document.getElementById('kpiHigh');
        const lowEl = document.getElementById('kpiLow');
        const changeEl = document.getElementById('kpiChange');
        const targetLabel = document.getElementById('kpiTargetSymbol');
        if (!closeEl) return; 

        // 獲取第一個活動中的股票代碼
        const targetSymbol = Array.from(activeSymbols)[0];
        
        if (!targetSymbol || !selectedTaskData[targetSymbol] || selectedTaskData[targetSymbol].length === 0) {
            [closeEl, highEl, lowEl, changeEl].forEach(el => el.textContent = '--');
            if (targetLabel) targetLabel.textContent = '';
            changeEl.style.color = 'var(--text-muted)';
            return;
        }

        if (targetLabel) targetLabel.textContent = `(${targetSymbol})`;
        
        const dataRecords = selectedTaskData[targetSymbol];
        const closes = dataRecords.map(r => parseFloat(r.close_price));
        const latest = closes[closes.length - 1];
        const high = Math.max(...closes);
        const low = Math.min(...closes);

        closeEl.textContent = latest.toFixed(2);
        highEl.textContent = high.toFixed(2);
        lowEl.textContent = low.toFixed(2);

        if (closes.length >= 2) {
            const prev = closes[closes.length - 2];
            const pct = ((latest - prev) / prev * 100).toFixed(2);
            const isUp = pct >= 0;
            changeEl.textContent = `${isUp ? '+' : ''}${pct}%`;
            changeEl.style.color = isUp ? 'var(--success)' : 'var(--danger)';
        } else {
            changeEl.textContent = 'N/A';
            changeEl.style.color = 'var(--text-muted)';
        }
    };

    const plotChart = () => {
        if (currentChart) {
            currentChart.destroy();
        }

        // 從活動中的數據集中收集所有不重複的日期，以形成 X 軸
        const allDates = new Set();
        Array.from(activeSymbols).forEach(sym => {
            const records = selectedTaskData[sym] || [];
            records.forEach(r => allDates.add(r.market_date));
        });
        const labels = Array.from(allDates).sort(); // 按時間順序排序 (Chronological)

        // 建立數據集
        const datasets = [];
        let colorIndex = 0;
        
        // 我們遍歷原始任務代碼以保持顏色穩定
        const currentTask = currentTasks.find(t => t.id.toString() === taskSelect.value);
        if (currentTask && currentTask.symbols) {
            currentTask.symbols.forEach((sym, idx) => {
                if (!activeSymbols.has(sym)) return;
                
                const records = selectedTaskData[sym] || [];
                // 將記錄映射到統一的標籤軸
                const dataMap = {};
                records.forEach(r => dataMap[r.market_date] = parseFloat(r.close_price));
                const data = labels.map(date => dataMap[date] || null);
                
                const c = colors[idx % colors.length];
                const onlyOneLine = activeSymbols.size === 1;

                datasets.push({
                    label: sym,
                    data: data,
                    yAxisID: sym,
                    borderColor: c.border,
                    backgroundColor: (context) => {
                        if (!onlyOneLine) return 'transparent';
                        const { ctx: ctx2d, chartArea } = context.chart;
                        if (!chartArea) return `${c.border}15`;
                        const gradient = ctx2d.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                        gradient.addColorStop(0, `${c.border}20`);
                        gradient.addColorStop(1, `${c.border}02`);
                        return gradient;
                    },
                    borderWidth: 3,
                    tension: 0.3,
                    fill: onlyOneLine,
                    pointRadius: onlyOneLine ? 4 : 1,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#ffffff',
                    pointBorderColor: c.border,
                    pointHoverBackgroundColor: c.border,
                    pointHoverBorderColor: '#ffffff',
                    pointHoverBorderWidth: 2,
                    spanGaps: true
                });
            });
        }

        // 動態建立軸標籤 (Scales)：為每支股票提供其獨立的線性比例軸
        const chartScales = {
            x: {
                grid: { color: 'rgba(0, 0, 0, 0.03)', drawBorder: false },
                ticks: { color: '#64748b', font: { size: 11, weight: '600' }, maxRotation: 0 }
            }
        };

        let axisCount = 0;
        Array.from(activeSymbols).forEach(sym => {
            const isLeft = (axisCount % 2 === 0);
            chartScales[sym] = {
                type: 'linear',
                display: axisCount < 2,
                position: isLeft ? 'left' : 'right',
                grid: {
                    color: isLeft ? 'rgba(0, 0, 0, 0.03)' : 'transparent',
                    drawBorder: false
                },
                ticks: {
                    color: '#64748b',
                    font: { size: 11, weight: '600' },
                    padding: 8
                }
            };
            axisCount++;
        });

        currentChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false // 我們使用自定義的切換按鈕
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: '#ffffff',
                        titleColor: '#1e293b',
                        bodyColor: '#475569',
                        borderColor: 'rgba(0, 0, 0, 0.08)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 10,
                        titleFont: { size: 13, weight: 'bold' },
                        bodyFont: { size: 13 },
                        boxPadding: 6,
                        usePointStyle: true,
                        callbacks: {
                            label: function(context) {
                                const sym = context.dataset.label;
                                const val = context.parsed.y;
                                return ` ${sym}: ${val.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: chartScales,
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    };

    taskSelect.addEventListener('change', (e) => loadTaskData(e.target.value));
    refreshBtn.addEventListener('click', () => loadTaskData(taskSelect.value));

    initSelectOptions();
});
