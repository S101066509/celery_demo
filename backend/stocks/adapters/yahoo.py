import datetime
from decimal import Decimal
import requests
from .base import BaseCrawlerAdapter

class YahooFinanceAdapter(BaseCrawlerAdapter):
    """
    Yahoo Finance 適配器。
    使用 Yahoo Chart API 抓取真實歷史股價數據。
    """
    def fetch(self, symbols: list):
        records = []
        errors = []
        
        # 抓取近 1 個月的每日數據以填充歷史紀錄
        params = {
            'range': '1mo',
            'interval': '1d',
            'events': 'history'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        for symbol in symbols:
            try:
                # Yahoo 要求代碼帶有正確的後綴（例: 台股用 2330.TW）
                # 此處假設美股直接使用代碼，或由呼叫端處理轉換
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                response = requests.get(url, params=params, headers=headers, timeout=10)
                
                if response.status_code != 200:
                    errors.append(f"HTTP {response.status_code} for {symbol}")
                    continue
                
                data = response.json()
                result = data.get('chart', {}).get('result', [])
                
                if not result:
                    errors.append(f"No results found for {symbol}")
                    continue
                
                chart_data = result[0]
                timestamps = chart_data.get('timestamp', [])
                indicators = chart_data.get('indicators', {}).get('quote', [{}])[0]
                
                # 解析 OHLCV 陣列
                opens = indicators.get('open', [])
                highs = indicators.get('high', [])
                lows = indicators.get('low', [])
                closes = indicators.get('close', [])
                volumes = indicators.get('volume', [])

                for i in range(len(timestamps)):
                    # 過濾 Yahoo 回傳的不完整數據
                    if None in [opens[i], highs[i], lows[i], closes[i]]:
                        continue

                    # 將 Unix 時間戳轉換為日期
                    dt = datetime.datetime.fromtimestamp(timestamps[i]).date()
                    
                    records.append({
                        "ticker": symbol,
                        "market_date": dt,
                        "open_price": Decimal(str(opens[i])),
                        "high_price": Decimal(str(highs[i])),
                        "low_price": Decimal(str(lows[i])),
                        "close_price": Decimal(str(closes[i])),
                        "volume": int(volumes[i]) if volumes[i] is not None else 0,
                        "source": "yahoo"
                    })
                    
            except Exception as e:
                errors.append(f"Failed to fetch {symbol} from Yahoo: {str(e)}")

        return {
            "status": "SUCCESS" if not errors else "PARTIAL" if records else "FAILED",
            "records": records,
            "errors": errors
        }
