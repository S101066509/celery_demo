import logging
from .yahoo import YahooFinanceAdapter

logger = logging.getLogger(__name__)

class TWSEAdapter(YahooFinanceAdapter):
    """
    台灣證券交易所的混合適配器。
    透過 Yahoo Finance API 取得台股歷史數據。
    原因：TWSE OpenAPI 的個股歷史端點不穩定。
    台股 Yahoo 代碼格式：{symbol}.TW
    """
    def fetch(self, symbols: list):
        # 1. 將代碼轉換為 Yahoo 格式（例: 2330 → 2330.TW）
        tw_symbols = []
        for s in symbols:
            clean = s.split('.')[0].strip()
            if len(clean) == 4 or len(clean) == 6: # 標準台股代碼
                tw_symbols.append(f"{clean}.TW")
            else:
                tw_symbols.append(s)
        
        # 2. 借用 Yahoo 的穩定歷史數據抓取邏輯
        # 會回傳多筆每日紀錄（近 1 個月）
        result = super().fetch(tw_symbols)
        
        # 3. 將來源標記為 'twse'，保持資料庫內部一致性
        if result.get("records"):
            for r in result["records"]:
                r["source"] = "twse"
                # 可選擇保留原始代碼（如 2330）或保留 .TW 格式
                # r["ticker"] = r["ticker"].split('.')[0] 
        
        return result
