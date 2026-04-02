from django.core.cache import cache
import requests

TWSE_CACHE_KEY = "twse:stock_day_all"
TWSE_CACHE_TTL = 60 * 60 * 12  # 12 hours

def sync_stock_directory_to_redis():
    """
    將資料庫 StockDirectory 資料表同步到 Redis，實現超快速搜尋。
    邏輯: cache.set('stock_dir:{market}', {ticker: name})
    """
    from ..models import StockDirectory
    
    markets = ['twse', 'yahoo']
    for m in markets:
        records = StockDirectory.objects.filter(market=m, is_active=True)
        data = {r.ticker: r.name for r in records}
        cache.set(f"stock_dir:{m}", data, timeout=None) # Forever cache
    
    print(">>> [Redis] Stock Directory Sync Completed.")

def refresh_twse_stock_day_all(force=False):
    """
    Fetch TWSE STOCK_DAY_ALL and cache for fast search suggestions.
    Returns cached dict: {Code: {...}} or None on failure.
    """
    if not force:
        cached = cache.get(TWSE_CACHE_KEY)
        if cached:
            return cached

    try:
        response = requests.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
            timeout=10
        )
        response.raise_for_status()
        raw_data = response.json()
        # Build dict indexed by Code for fast lookup
        data = {item.get('Code'): item for item in raw_data if item.get('Code')}
        cache.set(TWSE_CACHE_KEY, data, timeout=TWSE_CACHE_TTL)
        print(">>> [Redis] TWSE stock_day_all cache refreshed.")
        return data
    except Exception as e:
        print(f">>> [Warning] TWSE cache refresh failed: {e}")
        return None
