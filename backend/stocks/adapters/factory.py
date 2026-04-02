from .yahoo import YahooFinanceAdapter
from .twse import TWSEAdapter

class DataAdapterFactory:
    """
    工廠類別：根據類型字串實例化對應的數據適配器。
    """
    _registry = {
        'yahoo': YahooFinanceAdapter,
        'twse': TWSEAdapter
    }
    
    @classmethod
    def get_adapter(cls, adapter_type):
        adapter_class = cls._registry.get(adapter_type.lower())
        if not adapter_class:
            raise ValueError(f"Unknown adapter type: {adapter_type}")
        return adapter_class()
