from django.apps import AppConfig


class StocksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stocks'

    def ready(self):
        import sys
        import stocks.signals
        
        # 僅在啟動應用服務時同步（排除 migrate/makemigrations 等管理指令）
        skip_cmds = {
            'migrate', 'makemigrations', 'collectstatic',
            'shell', 'dbshell', 'createsuperuser', 'test',
        }
        if not any(cmd in sys.argv for cmd in skip_cmds):
            from .utils import sync_stock_directory_to_redis
            from django.db import connection
            
            # 先檢查資料表是否存在，避免在初始遷移時發生崩潰
            try:
                table_name = 'stocks_stockdirectory'
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}'")
                    exists = cursor.fetchone()
                
                if exists:
                    sync_stock_directory_to_redis()
                else:
                    print(f">>> [Info] Redis Sync deferred: Table {table_name} not found yet.")
            except Exception as e:
                print(f">>> [Warning] Redis Sync skipped: {e}")
