from django.db import models

class StockTask(models.Model):
    STATUS_CHOICES = (
        ('IDLE', 'Idle'),
        ('RUNNING', 'Running'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    )

    name = models.CharField(max_length=255, help_text="任務名稱 (例: 每日台股盤後數據)")
    adapter_type = models.CharField(max_length=50, help_text="指定適配器類型 (例: twse, yahoo)")
    symbols = models.JSONField(help_text='股票代碼清單 ["2330", "2317"]')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IDLE', help_text="最後一次執行結果")
    schedule_time = models.TimeField(null=True, blank=True, help_text="使用者定義的執行時間")
    last_run_at = models.DateTimeField(null=True, blank=True, help_text="最後一次啟動時間")
    is_active = models.BooleanField(default=True, help_text="是否啟用該排程")

    def __str__(self):
        return f"{self.name} ({self.adapter_type})"


class Execution(models.Model):
    STATUS_CHOICES = (
        ('STARTED', 'Started'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    )

    task = models.ForeignKey(StockTask, on_delete=models.CASCADE, related_name='executions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='STARTED')
    records_count = models.IntegerField(default=0, help_text="本次成功處理的資料筆數")
    started_at = models.DateTimeField(auto_now_add=True, help_text="開始執行時間")
    finished_at = models.DateTimeField(null=True, blank=True, help_text="完成時間")
    error_log = models.TextField(null=True, blank=True, help_text="失敗時的錯誤訊息")

    def __str__(self):
        return f"Execution for {self.task.name} at {self.started_at}"


class StockPrice(models.Model):
    ticker = models.CharField(max_length=50, help_text="股票代碼")
    market_date = models.DateField(help_text="市場歷史日期 (K線圖時間點)")
    open_price = models.DecimalField(max_digits=12, decimal_places=4, help_text="開盤價")
    high_price = models.DecimalField(max_digits=12, decimal_places=4, help_text="最高價")
    low_price = models.DecimalField(max_digits=12, decimal_places=4, help_text="最低價")
    close_price = models.DecimalField(max_digits=12, decimal_places=4, help_text="收盤價")
    volume = models.BigIntegerField(help_text="成交量")
    source = models.CharField(max_length=50, help_text="數據來源 (例: yahoo, twse)")
    created_at = models.DateTimeField(auto_now_add=True, help_text="存檔時間")

    class Meta:
        unique_together = ['ticker', 'market_date', 'source']
        ordering = ['-market_date']

    def __str__(self):
        return f"{self.ticker} on {self.market_date} by {self.source}"

class StockDirectory(models.Model):
    """
    證券主檔目錄：所有支援的股票代碼中央目錄。
    用於快速搜尋與自動補全。
    """
    MARKET_CHOICES = (
        ('twse', '台灣證券交易所'),
        ('yahoo', 'Yahoo 全球'),
    )

    ticker = models.CharField(max_length=50, db_index=True, help_text="股票代碼 (例: 2330, AAPL)")
    name = models.CharField(max_length=255, help_text="公司名稱 (例: 台積電, Tesla Inc.)")
    market = models.CharField(max_length=50, choices=MARKET_CHOICES, db_index=True)
    alias = models.CharField(max_length=255, null=True, blank=True, help_text="搜尋別名 (例: TSMC)")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['ticker', 'market']
        verbose_name_plural = "證券主檔目錄"

    def __str__(self):
        return f"[{self.market.upper()}] {self.ticker} - {self.name}"


class ErrorLog(models.Model):
    """系統全域錯誤追蹤的集中化錯誤記錄檔。"""

    LEVEL_CHOICES = (
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    )

    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='ERROR', db_index=True)
    source = models.CharField(max_length=255, help_text="來源模組 (e.g. stocks.tasks)")
    task = models.ForeignKey(
        StockTask, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='error_logs',
        help_text="關聯的數據任務（如適用）"
    )
    message = models.TextField(help_text="錯誤摘要")
    traceback = models.TextField(blank=True, default='', help_text="完整的 traceback")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.level}] {self.source}: {self.message[:80]}"
