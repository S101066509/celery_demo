import logging
import traceback
from celery.signals import task_failure
from ..models import ErrorLog, StockTask

logger = logging.getLogger(__name__)

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

@receiver(post_save, sender=StockTask)
def sync_periodic_task(sender, instance, created, **kwargs):
    """
    當 StockTask 被儲存時，自動同步建立或更新 Celery Beat 排程。
    """
    task_name = f"Run Stock Task: {instance.name} (ID:{instance.id})"
    
    # 如果任務不啟用，或者沒有設定時間，則刪除現有的排程
    if not instance.is_active or not instance.schedule_time:
        PeriodicTask.objects.filter(name=task_name).delete()
        return

    # 建立或取得 Crontab 排程 (每日固定時間執行)
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute=instance.schedule_time.minute,
        hour=instance.schedule_time.hour,
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
        timezone='Asia/Taipei'
    )

    # 建立或更新週期性任務
    PeriodicTask.objects.update_or_create(
        name=task_name,
        defaults={
            'crontab': schedule,
            # Use full import path so worker can resolve the task.
            'task': 'stocks.tasks.data_tasks.run_data_task',
            'args': json.dumps([instance.id]),
            'enabled': True,
        }
    )

@receiver(post_delete, sender=StockTask)
def delete_periodic_task(sender, instance, **kwargs):
    """
    當任務從資料庫移除時，連同排程一併清理。
    """
    task_name = f"Run Stock Task: {instance.name} (ID:{instance.id})"
    PeriodicTask.objects.filter(name=task_name).delete()

@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, traceback_obj=None, einfo=None, args=None, kwargs=None, **extra):
    """
    全域 Celery 信號處理器，攔截 Worker 中所有任務失敗事件。
    即使任務內部沒有被 try/except 捕捉到的例外，
    也能確保錯誤被記錄到 ErrorLog 資料表中。
    """
    source = f"celery.task.{sender.name if hasattr(sender, 'name') else 'unknown'}"
    
    # 嘗試從任務參數中提取 StockTask ID
    task_instance = None
    if args and len(args) > 0:
        try:
            # 假設 task_id 是我們自定義任務的第一個參數
            task_instance = StockTask.objects.filter(id=args[0]).first()
        except:
            pass

    ErrorLog.objects.create(
        level='CRITICAL',
        source=source,
        task=task_instance,
        message=str(exception),
        traceback=str(einfo) if einfo else traceback.format_exc()
    )
    logger.error(f"Celery Task Failure Logged: {sender} - {exception}")
