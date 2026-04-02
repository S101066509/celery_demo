from rest_framework import serializers
from .models import StockTask, Execution, StockPrice, ErrorLog

class StockTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTask
        fields = '__all__'
        read_only_fields = ('status', 'last_run_at')

class ExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Execution
        fields = '__all__'
        read_only_fields = ('task', 'status', 'records_count', 'started_at', 'finished_at', 'error_log')

class StockPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockPrice
        fields = '__all__'

class ErrorLogSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source='task.name', read_only=True, default=None)

    class Meta:
        model = ErrorLog
        fields = ['id', 'level', 'source', 'task', 'task_name', 'message', 'traceback', 'created_at']
