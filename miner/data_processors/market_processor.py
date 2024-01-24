import asyncio
import logging
import datetime
import settings

class MarketProcessor:
    def __init__(self, exchange_client):
        self.exchange_client = exchange_client

    async def process_markets(self, data):
        is_async = await self.exchange_client.initialize(data['exchange_id'])
        eligible_markets = []
        error_markets = []

        time_to_check_back = int(data['time_to_check_back'])
        time_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=time_to_check_back)
        parsed_time_ago = self.exchange_client.exchange.parse8601(time_ago.isoformat())

        for market in data['markets']:
            try:
                print(f"\rProcessing {market}                   ", end='')
                ohlcv = await self.exchange_client.fetch_ohlcv_data(market, since=parsed_time_ago, limit=time_to_check_back, time_units='1m', is_async=is_async)

                for candle in ohlcv:
                    open_price = candle[1]  # Open price is the second item in the candle list
                    close_price = candle[4]  # High price is the third item in the candle list
                    volume = candle[5]  # Volume is the sixth item in the candle list
                    
                    # Check if the high price is 1.5 times more than the open price
                    if close_price > (open_price * 1.5):
                        eligible_markets.append(market)
                        print(f"\nEligible market: {market} with open price: {open_price}, high price: {close_price}, volume: {volume}\n")
            
                await asyncio.sleep(settings.QUERY_DELAY) 

            except Exception as e:
                logging.error(f"\nError for market {market}: {e}, delay: {settings.QUERY_DELAY}\n")
                error_markets.append(market)
                settings.QUERY_DELAY = min(settings.QUERY_DELAY + 0.1, settings.MAX_QUERY_DELAY)
                await asyncio.sleep(settings.QUERY_DELAY)

        await self.exchange_client.close()
        return {'eligible_markets': eligible_markets, 'error_markets': error_markets}
