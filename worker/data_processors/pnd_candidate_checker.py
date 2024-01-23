import datetime
import asyncio
import logging
from utils.market_data_fetcher import fetch_market_cap
import settings

class PNDCandidateChecker:
    def __init__(self, exchange_client):
        self.exchange_client = exchange_client

    async def check(self, data):
        is_async = await self.exchange_client.initialize(data['exchange_id'])
        eligible_markets = []
        error_markets = []

        time_to_check_back = 7
        time_ago = datetime.datetime.utcnow() - datetime.timedelta(days=time_to_check_back)
        time_units = "1d"
        parsed_time_ago = self.exchange_client.exchange.parse8601(time_ago.isoformat())
        coinmarketcup_api_key = data['coinmarketcup_api_key']
        maximum_markey_cup = data['maximum_market_cup']

        for market in data['markets']:
            try:
                print(f"\rProcessing {market}                   ", end='')
                
                ohlcv = await self.exchange_client.fetch_ohlcv_data(market, since=parsed_time_ago, limit=time_to_check_back, time_units=time_units, is_async=is_async)
                
                # Initialize variables to store the first and last volume
                first_volume = None
                last_volume = None

                for index, candle in enumerate(ohlcv):
                    open_price = candle[1]  # Open price
                    close_price = candle[4]  # Close price
                    volume = candle[5]  # Volume

                    # Capture the first volume
                    if index == 0:
                        first_volume = volume

                    if volume > 1000:
                        continue

                    # Capture the last volume
                    last_volume = volume

                # Ensure that the first and last volumes are valid and calculate the percentage change
                if first_volume and last_volume:
                    volume_change_percentage = ((last_volume - first_volume) / first_volume) * 100

                    # Check if the volume change percentage is greater than 10% and the closing price is less than 10% of the opening price
                    if volume_change_percentage < 10 and close_price > open_price:
                        if coinmarketcup_api_key:
                            symbol, quote_currency = market.split('/')
                            market_cup = await fetch_market_cap(symbol, quote_currency, coinmarketcup_api_key)
                            if market_cup < maximum_markey_cup:
                                eligible_markets.append(market)
                                print(f"\nEligible market: {market} with market cup change {market_cup:.2f}")

                await asyncio.sleep(settings.QUERY_DELAY)

            except Exception as e:
                logging.error(f"\nError for market {market}: {e}, delay: {self.settings.query_delay}\n")
                error_markets.append(market)
                settings.QUERY_DELAY = min(settings.QUERY_DELAY + 0.1, settings.MAX_QUERY_DELAY)  # Increase delay but cap it
                await asyncio.sleep(settings.QUERY_DELAY)

        # Close the exchange properly based on its type
        await self.exchange_client.close()

        return {'eligible_markets': eligible_markets, 'error_markets': error_markets}
