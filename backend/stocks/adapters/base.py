from abc import ABC, abstractmethod

class BaseCrawlerAdapter(ABC):
    """
    所有爬蟲適配器的抽象基底類別 (ABC)。
    """
    @abstractmethod
    def fetch(self, symbols: list):
        """
        根據給定的股票代碼清單抓取數據。
        應回傳包含狀態、錯誤與抓取記錄的字典。
        """
        pass
