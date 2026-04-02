import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from stocks.models import StockDirectory
from stocks.utils import sync_stock_directory_to_redis
from django.core.cache import cache

TWSE_CACHE_KEY = "twse:stock_day_all"

def force_populate_twse():
    print(">>> [Force] Fetching live TWSE directory...")
    try:
        response = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=10)
        response.raise_for_status()
        raw_data = response.json()
        
        print(f">>> Found {len(raw_data)} stocks. Saving to Database...")

        # Cache raw data for quick search (keyed by Code)
        cache.set(
            TWSE_CACHE_KEY,
            {item.get('Code'): item for item in raw_data if item.get('Code')},
            timeout=60 * 60 * 12
        )
        
        objs = [
            StockDirectory(
                ticker=item['Code'],
                name=item.get('Name', 'Taiwan Stock'),
                market='twse'
            ) for item in raw_data
        ]
        
        StockDirectory.objects.bulk_create(objs, ignore_conflicts=True)
        print(">>> DB Update Complete. Syncing to Redis...")
        sync_stock_directory_to_redis()
        print(">>> [Success] Directory is now READY for search.")
    except Exception as e:
        print(f">>> [Error] Failed to force populate: {e}")

if __name__ == "__main__":
    force_populate_twse()
