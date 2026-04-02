import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.cache import cache
from stocks.models import StockTask

class CrawlerAPITest(APITestCase):

    def setUp(self):
        self.task = StockTask.objects.create(
            name="Test Task API",
            adapter_type="yahoo",
            symbols=["AAPL"]
        )
        # 需要在之後使用 unittest.mock 來模擬 celery delay
        # 由於我們使用標準快取做鎖定機制，確保測試開始時清空快取
        cache.clear()

    def test_get_tasks_list(self):
        """測試能否正確取得任務清單"""
        url = '/api/v1/tasks/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 僅檢查是否包含我們建立的特定任務（因為 signals 或預設物件可能也存在）
        if 'results' in response.data:
            task_names = [task['name'] for task in response.data['results']]
        else:
            task_names = [task['name'] for task in response.data]
            
        self.assertIn("Test Task API", task_names)

    def test_create_task(self):
        """測試透過 POST 建立新任務"""
        url = '/api/v1/tasks/'
        data = {
            "name": "New API Task",
            "adapter_type": "twse",
            "symbols": ["2330", "2317"],
            "schedule_time": "18:00:00"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(StockTask.objects.count(), 2)

    def test_trigger_execution(self):
        """測試透過 POST /tasks/{id}/executions/ 觸發一次執行"""
        from unittest import mock
        with mock.patch('stocks.tasks.run_data_task.delay') as mock_delay:
            url = reverse('task-executions', kwargs={'task_id': self.task.id})
            response = self.client.post(url)
            
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertIn("message", response.data)
            mock_delay.assert_called_once_with(self.task.id)

    def test_trigger_execution_conflict(self):
        """測試當鎖定已存在時觸發執行應回傳衝突"""
        url = reverse('task-executions', kwargs={'task_id': self.task.id})
        
        # 模擬已啟用的鎖
        lock_key = f"lock:task:{self.task.id}"
        cache.set(lock_key, "locked", timeout=60)
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("error", response.data)
        
        cache.delete(lock_key)
