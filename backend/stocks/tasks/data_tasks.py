import logging
import traceback as tb_module
from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.db import IntegrityError
from ..models import StockTask, Execution, StockPrice, ErrorLog
from ..adapters.factory import DataAdapterFactory

logger = logging.getLogger(__name__)

# 鎖定的存活時間 (TTL) 設定為 30 分鐘，以防止在 worker 當機時發生死鎖
LOCK_TTL = 30 * 60

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3}, retry_backoff=True)
def run_data_task(self, task_id):
    """
    執行數據任務。
    透過 Redis 實作分散式鎖 (Distributed Lock)，以防止相同任務的並發執行。
    """
    lock_key = f"lock:task:{task_id}"
    
    # 嘗試獲取鎖
    # 使用 Django 的快取框架（已配置為使用 Redis）
    if not cache.add(lock_key, "locked", timeout=LOCK_TTL):
        logger.warning(f"任務 {task_id} 正在運行中。跳過此次執行。")
        return f"跳過 - 任務 {task_id} 已被鎖定。"

    try:
        task = StockTask.objects.get(id=task_id)
        
        # 建立一個 Execution 紀錄來追蹤此次執行情況
        execution = Execution.objects.create(
            task=task,
            status='STARTED'
        )
        
        task.status = 'RUNNING'
        task.last_run_at = timezone.now()
        task.save()

        # 獲取相對應的適配器 (Adapter)
        try:
            adapter = DataAdapterFactory.get_adapter(task.adapter_type)
        except ValueError as e:
            execution.status = 'FAILED'
            execution.error_log = str(e)
            execution.finished_at = timezone.now()
            execution.save()
            
            task.status = 'FAILED'
            task.save()

            ErrorLog.objects.create(
                level='ERROR',
                source='stocks.tasks.run_data_task',
                task=task,
                message=str(e),
                traceback=tb_module.format_exc()
            )
            return f"Failed - {str(e)}"

        # 抓取數據
        result = adapter.fetch(task.symbols)
        
        # 將記錄存入資料庫
        records_saved = 0
        if result.get("records"):
            for record_data in result["records"]:
                try:
                    # 使用 update_or_create：以 ticker + market_date 作為唯一標識
                    # 如果已存在則更新 price/volume，不存在則新增
                    ticker = record_data.get('ticker')
                    market_date = record_data.get('market_date')
                    source = record_data.get('source')
                    
                    # 確保這三個唯一鍵不在 defaults 裡，而是作為查詢條件
                    defaults = record_data.copy()
                    del defaults['ticker']
                    del defaults['market_date']
                    del defaults['source']

                    StockPrice.objects.update_or_create(
                        ticker=ticker,
                        market_date=market_date,
                        source=source,
                        defaults=defaults
                    )
                    records_saved += 1
                except Exception as e:
                    logger.error(f"儲存記錄失敗: {str(e)}")
                    ErrorLog.objects.create(
                        level='WARNING',
                        source='stocks.tasks.run_data_task',
                        task=task,
                        message=f"Failed to save record for {record_data.get('ticker', '?')}: {str(e)}",
                    )
                    pass

        # 更新執行狀態
        execution.status = 'SUCCESS' if not result.get("errors") else 'FAILED'
        execution.records_count = records_saved
        execution.error_log = "\n".join(result.get("errors", []))
        execution.finished_at = timezone.now()
        execution.save()

        # 將適配器層級的錯誤寫入 ErrorLog
        if result.get("errors"):
            for err_msg in result["errors"]:
                ErrorLog.objects.create(
                    level='ERROR',
                    source=f'stocks.adapters.{task.adapter_type}',
                    task=task,
                    message=err_msg,
                )

        # 更新任務狀態
        task.status = 'SUCCESS' if not result.get("errors") else 'FAILED'
        task.save()

        return f"已完成 - 儲存了 {records_saved} 筆記錄。狀態: {execution.status}"

    finally:
        # 完成後務必釋放鎖
        cache.delete(lock_key)
