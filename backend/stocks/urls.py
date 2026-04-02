from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.i18n import JavaScriptCatalog
from .views import (
    StockTaskViewSet, ExecutionListCreateView, StockPriceViewSet, ErrorLogViewSet,
    SystemHealthView, YahooSearchProxyView, dashboard_view, settings_view, charts_view, error_logs_view
)

# ---------------------------------------------------------
# 1. API 路由 (DRF Viewsets 與 APIViews)
# ---------------------------------------------------------
router = DefaultRouter()
router.register(r'tasks', StockTaskViewSet)
router.register(r'prices', StockPriceViewSet)
router.register(r'errors', ErrorLogViewSet)

api_patterns = [
    path('', include(router.urls)),
    path('tasks/<int:task_id>/executions/', ExecutionListCreateView.as_view(), name='task-executions'),
    path('health/', SystemHealthView.as_view(), name='system-health'),
    path('proxy/search/', YahooSearchProxyView.as_view(), name='yahoo-search-proxy'),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
]

# ---------------------------------------------------------
# 2. 頁面路由 (HTML 模板渲染)
# ---------------------------------------------------------
urlpatterns = [
    # 前端頁面
    path('', dashboard_view, name='dashboard'),
    path('data/settings/', settings_view, name='task_settings'),
    path('prices/charts/', charts_view, name='stock_charts'),
    path('logs/errors/', error_logs_view, name='error_logs'),
]
