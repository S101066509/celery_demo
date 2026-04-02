from django.contrib import admin
from .models import StockTask, Execution, StockPrice, StockDirectory, ErrorLog

@admin.register(StockTask)
class StockTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'adapter_type', 'status', 'is_active', 'last_run_at')
    list_filter = ('status', 'adapter_type', 'is_active')
    search_fields = ('name',)

@admin.register(Execution)
class ExecutionAdmin(admin.ModelAdmin):
    list_display = ('task', 'status', 'records_count', 'started_at', 'finished_at')
    list_filter = ('status',)

@admin.register(StockPrice)
class StockPriceAdmin(admin.ModelAdmin):
    list_display = ('ticker', 'market_date', 'close_price', 'volume', 'source')
    list_filter = ('source', 'market_date')
    search_fields = ('ticker',)

@admin.register(StockDirectory)
class StockDirectoryAdmin(admin.ModelAdmin):
    list_display = ('ticker', 'name', 'market', 'is_active')
    list_filter = ('market', 'is_active')
    search_fields = ('ticker', 'name')

@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ('level', 'source', 'task', 'message', 'created_at')
    list_filter = ('level', 'created_at')
    search_fields = ('message', 'source')
