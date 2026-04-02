import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from stocks.models import StockDirectory
from django.core.cache import cache

def seed_twse_directory():
    """
    Populate StockDirectory with data from existing TWSE cache if available.
    """
    twse_data = cache.get("twse:stock_day_all")
    if not twse_data:
        print(">>> No TWSE cache found. Please run a TWSE task first.")
        return

    count = 0
    for ticker, info in twse_data.items():
        obj, created = StockDirectory.objects.update_or_create(
            ticker=ticker,
            market='twse',
            defaults={
                'name': info.get('Name', 'Unknown'),
            }
        )
        if created: count += 1
    
    print(f">>> Seeded {count} new TWSE stocks into Directory.")

if __name__ == "__main__":
    seed_twse_directory()
    from stocks.utils import sync_stock_directory_to_redis
    sync_stock_directory_to_redis()
