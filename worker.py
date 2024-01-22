import json
import ccxt
import ccxt.async_support as ccxtpro
import logging
import datetime
import asyncio
import websockets
import os
import aiohttp
from dotenv import load_dotenv

exchange = None
ws = None

query_delay = 1
MAX_QUERY_DELAY = 5.0

exchange = None

# New helper function to initialize the exchange
async def initialize_exchange(data):
    global exchange
    if hasattr(ccxtpro, data['exchange_id']):
        exchange_class = getattr(ccxtpro, data['exchange_id'])
        exchange = exchange_class({'enableRateLimit': True})
        return True  # Async supported
    else:
        exchange_class = getattr(ccxt, data['exchange_id'])
        exchange = exchange_class({'enableRateLimit': True})
        return False  # Async not supported

# New helper function to fetch OHLCV data
async def fetch_ohlcv_data(market, since, limit, time_units, is_async):
    if is_async:
        return await exchange.fetch_ohlcv(market, time_units, since=since, limit=limit)
    else:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: exchange.fetch_ohlcv(market, time_units, since, limit))


async def process_data(data):

    if data['task'] == 'process_market_data':
        return await process_markets(data)
    elif data['task'] == 'process_orders_book':
        pass
    elif data['task'] == 'process_ticker':
        pass
    elif data['task'] == 'check_pnd_candidates':
        return await check_pnd_candidates(data)
    elif data['task'] == 'shutdown':
        logging.info("\nWorker stopped from master\n")
        asyncio.run(cleanup())
    
async def check_pnd_candidates(data):
    global query_delay

    is_async = await initialize_exchange(data)

    eligible_markets = []
    error_markets = []

    time_to_check_back = 7
    time_ago = datetime.datetime.utcnow() - datetime.timedelta(days=time_to_check_back)
    time_units = "1d"
    parsed_time_ago = exchange.parse8601(time_ago.isoformat())
    coinmarketcup_api_key = data['coinmarketcup_api_key']
    maximum_markey_cup = data['maximum_market_cup']

    for market in data['markets']:
        try:
            print(f"\rProcessing {market}                   ", end='')
            
            ohlcv = await fetch_ohlcv_data(market, since=parsed_time_ago, limit=time_to_check_back, time_units=time_units, is_async=is_async)
            
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

            await asyncio.sleep(query_delay)

        except Exception as e:
            logging.error(f"\nError for market {market}: {e}, delay: {query_delay}\n")
            error_markets.append(market)
            query_delay = min(query_delay + 0.1, MAX_QUERY_DELAY)  # Increase delay but cap it
            await asyncio.sleep(query_delay)

    # Close the exchange properly based on its type
    if is_async:
        await exchange.close()
    else:
        exchange.close()

    return {'eligible_markets': eligible_markets, 'error_markets': error_markets}


async def process_markets(data):
    global query_delay
    is_async = await initialize_exchange(data)

    eligible_markets = []
    error_markets = []

    time_to_check_back = int(data['time_to_check_back'])
    time_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=time_to_check_back)
    parsed_time_ago = exchange.parse8601(time_ago.isoformat())

    for market in data['markets']:
        try:
            print(f"\rProcessing {market}                   ", end='')

            ohlcv = await fetch_ohlcv_data(market, since=parsed_time_ago, limit=time_to_check_back, time_units='1m', is_async=is_async)

            for candle in ohlcv:
                # timestamp = candle[0]
                open_price = candle[1]  # Open price is the second item in the candle list
                high_price = candle[2]  # High price is the third item in the candle list
                # close_price = candle[4]  # Close price is the fifth item in the candle list
                volume = candle[5]  # Volume is the sixth item in the candle list
                
                # Check if the high price is 1.5 times more than the open price, 
                # and the volume changed from less than 'prev_volume' to more than 'next_volume'
                if high_price > (open_price * 1.5):
                    eligible_markets.append(market)
                    print(f"\nEligible market: {market} with open price: {open_price}, high price: {high_price}, volume: {volume}\n")
        
            await asyncio.sleep(query_delay) 

        except Exception as e:
            logging.error(f"\nError for market {market}: {e}, delay: {query_delay}\n")
            error_markets.append(market)
            query_delay = min(query_delay + 0.1, MAX_QUERY_DELAY)  # Increase delay but cap it
            await asyncio.sleep(query_delay)

    # Close the exchange properly based on its type
    if is_async:
        await exchange.close()
    else:
        exchange.close()

    return {'eligible_markets': eligible_markets, 'error_markets': error_markets}

async def send_response(websocket, response_data):
    response = json.dumps(response_data)
    await websocket.send(response)

async def handle_data(websocket):
    global ws
    ws = websocket
    try:
        while True:  # Keep listening for data
            message = await websocket.recv()
            data = json.loads(message)
            result = await process_data(data)
            await send_response(websocket, result)

    except websockets.ConnectionClosed as e:
        logging.error(f"Connection closed: {e}")
        raise  # Re-raise to handle reconnection outside

    except Exception as e:
        print(f"An error occurred while handling data: {e}")

async def fetch_market_cap(symbol: str, quote_currency: str, api_key: str) -> float:
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {
        "X-CMC_PRO_API_KEY": api_key,
        "Accept": "application/json"
    }
    params = {
        "symbol": symbol,
        "convert": quote_currency
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                market_cap = data['data'][symbol]['quote']['USD']['market_cap']
                return market_cap
            else:
                # Handle errors (you might want to raise an exception or return None)
                print(f"Error fetching market cap: {response.status}")
                return None

async def connect_to_server(uri):
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                logging.info(f"Connected to {uri}")
                while True:
                    await handle_data(websocket)
        except websockets.ConnectionClosed as e:
            logging.error(f"Connection closed: {e}, attempting to reconnect...")
        except Exception as e:
            logging.error(f"An error occurred: {e}")
        await asyncio.sleep(10)  # Wait a bit before retrying to avoid hammering the server


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    load_dotenv()
    uri = os.getenv('URI') 
    await connect_to_server(uri)

async def cleanup():
    global exchange
    if exchange:
        await exchange.close()
        logging.info("Exchange closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nWorker stopped manually\n")
        asyncio.run(cleanup())
    except Exception as e:
        logging.error(f"\nError in worker: {e}\n")
