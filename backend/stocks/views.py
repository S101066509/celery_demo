import requests
import traceback
from django.shortcuts import render
from django.core.cache import cache
from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import StockTask, Execution, StockPrice, ErrorLog
from .serializers import StockTaskSerializer, ExecutionSerializer, StockPriceSerializer, ErrorLogSerializer
from .tasks import run_data_task
from config.celery import app as celery_app
from django.db import connection
from django.utils.translation import gettext_lazy as _
from .utils import refresh_twse_stock_day_all

# =============================================================================
# 1. 頁面視圖 (HTML 渲染)
# 這些視圖負責向瀏覽器提供實際的網頁。
# =============================================================================

def dashboard_view(request):
    """ 主儀表板視圖：列出所有任務與總體狀態。 """
    return render(request, 'stocks/dashboard.html')

def settings_view(request):
    """ 設定視圖：建立/編輯數據任務的介面。 """
    return render(request, 'stocks/settings.html')

def charts_view(request):
    """ 圖表視圖：可視化股價數據。 """
    return render(request, 'stocks/charts.html')

def error_logs_view(request):
    """ 錯誤日誌視圖：顯示系統錯誤歷史。 """
    return render(request, 'stocks/error_logs.html')


# =============================================================================
# 2. API 視圖集 (REST Framework / JSON)
# 這些端點將數據傳回給前端 JavaScript。
# =============================================================================

class StockTaskViewSet(viewsets.ModelViewSet):
    """ 任務 CRUD 操作的 API 端點。 """
    queryset = StockTask.objects.all().order_by('-id')
    serializer_class = StockTaskSerializer

class ExecutionListCreateView(generics.ListCreateAPIView):
    """ 用於觸發與列出手動任務執行紀錄的 API 端點。 """
    serializer_class = ExecutionSerializer

    def get_queryset(self):
        task_id = self.kwargs.get('task_id')
        return Execution.objects.filter(task_id=task_id).order_by('-started_at')

    def create(self, request, *args, **kwargs):
        task_id = self.kwargs.get('task_id')
        try:
            task = StockTask.objects.get(id=task_id)
        except StockTask.DoesNotExist:
            return Response({"error": _("Task not found.")}, status=status.HTTP_404_NOT_FOUND)

        lock_key = f"lock:task:{task_id}"
        if cache.get(lock_key):
            return Response(
                {"error": _("Task is already currently running. Please wait preventing duplicate execution.")}, 
                status=status.HTTP_409_CONFLICT
            )

        try:
            run_data_task.delay(task.id)
        except Exception as e:
            # 處理派發任務時的 Celery/Redis 連線失敗
            ErrorLog.objects.create(
                level='CRITICAL',
                source='stocks.views.ExecutionCreate',
                task=task,
                message=f"Celery dispatch failed: {str(e)}",
                traceback=traceback.format_exc()
            )
            return Response(
                {"error": _("Failed to queue task. System connection issue.")}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"message": _("Task received and is processing asynchronously."), "task_id": task.id},
            status=status.HTTP_202_ACCEPTED
        )

class StockPriceViewSet(viewsets.ReadOnlyModelViewSet):
    """ 專門用於獲取圖表數據的 API 端點。 """
    queryset = StockPrice.objects.all()
    serializer_class = StockPriceSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = StockPrice.objects.all().order_by('market_date')
        ticker = self.request.query_params.get('ticker')
        if ticker:
            # 支援 2330 匹配 2330.TW
            queryset = queryset.filter(ticker__contains=ticker)
        
        source = self.request.query_params.get('source')
        if source:
            queryset = queryset.filter(source=source)
            
        return queryset


class ErrorLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ 用於瀏覽錯誤日誌的唯讀 API 端點。 """
    queryset = ErrorLog.objects.select_related('task').all()
    serializer_class = ErrorLogSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['level']
    ordering_fields = ['created_at', 'level']
    ordering = ['-created_at']


# =============================================================================
# 3. 系統視圖
# =============================================================================

class SystemHealthView(APIView):
    """
    檢查核心系統組件（Django DB, Redis, Celery Workers）的健康狀況。
    """
    def get(self, request):
        status_data = {
            "database": "offline",
            "redis": "offline",
            "celery": "offline"
        }
        all_ok = True

        # 檢查資料庫
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            status_data["database"] = "online"
        except Exception as e:
            all_ok = False
            status_data["database"] = f"error: {str(e)}"
            ErrorLog.objects.get_or_create(
                level='CRITICAL',
                source='system.health.database',
                message=f"資料庫連線失敗: {str(e)}"
            )

        # 檢查 Redis (透過 Django Cache)
        try:
            cache.set('health_ping', 'pong', timeout=1)
            if cache.get('health_ping') == 'pong':
                status_data["redis"] = "online"
            else:
                all_ok = False
                ErrorLog.objects.get_or_create(
                    level='ERROR',
                    source='system.health.redis',
                    message="Redis 測試失敗 (Cache 傳回 None)"
                )
        except Exception as e:
            all_ok = False
            status_data["redis"] = f"error: {str(e)}"
            ErrorLog.objects.get_or_create(
                level='ERROR',
                source='system.health.redis',
                message=f"Redis 連線失敗: {str(e)}"
            )

        # 檢查 Celery Workers (需要 Redis 正常)
        if status_data["redis"] == "online":
            try:
                i = celery_app.control.inspect(timeout=1.0)
                ping_res = i.ping()
                if ping_res:
                    status_data["celery"] = "online"
                else:
                    status_data["celery"] = "offline (沒有活動中的 worker)"
                    all_ok = False
                    ErrorLog.objects.get_or_create(
                        level='CRITICAL',
                        source='system.health.celery',
                        message="Celery 斷線: 找不到活動中的 worker"
                    )
            except Exception as e:
                status_data["celery"] = f"error: {str(e)}"
                all_ok = False
                ErrorLog.objects.get_or_create(
                    level='CRITICAL',
                    source='system.health.celery',
                    message=f"Celery 檢查失敗: {str(e)}"
                )
        else:
            status_data["celery"] = "offline (redis 已斷線)"
            all_ok = False

        status_code = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response({
            "status": "healthy" if all_ok else "unhealthy",
            "components": status_data
        }, status=status_code)

# =============================================================================
# 4. 代理 (Proxy) 與工具視圖
# 外部 API 代理，簡化前端開發並處理 CORS。
# =============================================================================

class YahooSearchProxyView(APIView):
    """
    統一的股票建議代理視圖。
    使用 StockDirectory (與 Redis 同步) 進行超快速本地查找。
    """
    def get(self, request):
        query = request.query_params.get('q', '').strip().upper()
        target = request.query_params.get('target', 'yahoo')
        
        if not query or len(query) < 1:
            return Response([])

        # --- 1. 優先嘗試 Redis 快取目錄 (StockDirectory 同步) ---
        dir_key = f"stock_dir:{target}"
        try:
            full_dir = cache.get(dir_key) # Format: {ticker: name}
            if full_dir:
                matches = []
                for ticker, name_val in full_dir.items():
                    # 比對股票代碼或公司名稱
                    if query in ticker or query in name_val.upper():
                        matches.append({
                            'symbol': ticker,
                            'shortname': name_val,
                            'typeDisp': 'EQUITY',
                            'exchDisp': target.upper()
                        })
                        if len(matches) >= 10: break
                if matches:
                    return Response(matches)
        except Exception as e:
            print(f">>> [Search Error] Redis lookup failed: {e}")

        # --- 2. 備援方案：使用適配器專用快取（如 TWSE 每日數據） ---
        if target == 'twse':
            market_data = cache.get("twse:stock_day_all")
            if not market_data:
                market_data = refresh_twse_stock_day_all()
            if market_data:
                matches = []
                for code, info in market_data.items():
                    if query in code or query in info.get('Name', '').upper():
                        matches.append({
                            'symbol': code,
                            'shortname': info.get('Name', ''),
                            'typeDisp': 'EQUITY',
                            'exchDisp': 'TWSE'
                        })
                        if len(matches) >= 10: break
                return Response(matches)

        # --- 3. 最終備援：即時查詢 Yahoo Search（僅限 Yahoo 來源） ---
        if target == 'yahoo' and len(query) >= 2:
            try:
                url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}"
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    quotes = data.get('quotes', [])
                    return Response([{
                        'symbol': q.get('symbol'),
                        'shortname': q.get('shortname', q.get('longname', '')),
                        'typeDisp': q.get('typeDisp', 'EQUITY'),
                        'exchDisp': q.get('exchDisp', '')
                    } for q in quotes if q.get('symbol')])
            except: pass # 即時搜尋失敗時靜默處理

        return Response([])
