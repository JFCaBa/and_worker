import ccxt
import ccxt.async_support as ccxtpro
import asyncio

class ExchangeClient:
    def __init__(self):
        self.exchange = None

    async def initialize(self, exchange_id):
        if hasattr(ccxtpro, exchange_id):
            exchange_class = getattr(ccxtpro, exchange_id)
            self.exchange = exchange_class({'enableRateLimit': True})
            return True  # Async supported
        else:
            exchange_class = getattr(ccxt, exchange_id)
            self.exchange = exchange_class({'enableRateLimit': True})
            return False  # Async not supported

    async def fetch_ohlcv_data(self, market, since, limit, time_units, is_async):
        if is_async:
            return await self.exchange.fetch_ohlcv(market, time_units, since=since, limit=limit)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self.exchange.fetch_ohlcv(market, time_units, since, limit))
    
    async def close(self):
        if hasattr(self.exchange, 'close'):
            await self.exchange.close()
        else:
            self.exchange.close()
