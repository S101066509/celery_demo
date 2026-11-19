from django.test import TestCase
from django.db import IntegrityError
from datetime import date
from stocks.models import StockTask, Execution, StockPrice

class CrawlerModelsTest(TestCase):

    def setUp(self):
        self.task = StockTask.objects.create(
            name="Test Task",
            adapter_type="yahoo",
            symbols=["AAPL", "GOOGL"]
        )

    def test_crawler_task_creation(self):
        """測試 StockTask 的建立與預設值"""
        self.assertEqual(self.task.name, "Test Task")
        self.assertEqual(self.task.adapter_type, "yahoo")
        self.assertEqual(self.task.status, "IDLE")
        self.assertTrue(self.task.is_active)

    def test_execution_creation(self):
        """測試 Execution 能正確關聯到 StockTask"""
        execution = Execution.objects.create(
            task=self.task,
            status="STARTED"
        )
        self.assertEqual(execution.task, self.task)
        self.assertEqual(execution.status, "STARTED")
        self.assertEqual(execution.records_count, 0)
        self.assertEqual(self.task.executions.count(), 1)

    def test_stock_price_unique_constraint(self):
        """測試 StockPrice 模型的 unique_together 約束"""
        today = date.today()
        
        # 建立第一筆記錄
        StockPrice.objects.create(
            ticker="AAPL",
            market_date=today,
            open_price=150.00,
            high_price=155.00,
            low_price=149.00,
            close_price=152.00,
            volume=1000000,
            source="yahoo"
        )
        
        # 嘗試建立完全相同的記錄應拋出 IntegrityError
        from django.db import transaction
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                StockPrice.objects.create(
                    ticker="AAPL",
                    market_date=today,
                    open_price=151.00, # 不同價格無關緊要，因為 ticker+date+source 是唯一約束
                    high_price=156.00,
                    low_price=150.00,
                    close_price=153.00,
                    volume=1200000,
                    source="yahoo"
                )
        
        # 使用不同來源建立記錄應可成功
        StockPrice.objects.create(
            ticker="AAPL",
            market_date=today,
            open_price=150.00,
            high_price=155.00,
            low_price=149.00,
            close_price=152.00,
            volume=1000000,
            source="twse" # 不同來源
        )

    def test_schedule_tracks_task_across_rename_and_disable(self):
        from datetime import time
        from django_celery_beat.models import PeriodicTask

        self.task.schedule_time = time(9)
        self.task.save()
        self.task.name = "Renamed"
        self.task.save()
        schedules = PeriodicTask.objects.filter(task="stocks.tasks.data_tasks.run_data_task")
        self.assertEqual(schedules.count(), 1)
        self.task.is_active = False
        self.task.save()
        self.assertFalse(schedules.exists())

    def test_failed_record_marks_execution_failed(self):
        from unittest.mock import patch
        from stocks.tasks import run_data_task

        with patch('stocks.tasks.data_tasks.DataAdapterFactory.get_adapter') as factory:
            factory.return_value.fetch.return_value = {"records": [{"ticker": "AAPL"}], "errors": []}
            run_data_task.run(self.task.pk)
        execution = self.task.executions.get()
        self.task.refresh_from_db()
        self.assertEqual(execution.status, "FAILED")
        self.assertEqual(self.task.status, "FAILED")
        self.assertEqual(execution.records_count, 0)
        self.assertIn("AAPL", execution.error_log)
