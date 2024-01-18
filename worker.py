import json
import ccxt.pro as ccxt
import logging
import datetime
import asyncio
import websockets
import os
from dotenv import load_dotenv

exchange = None
ws = None

async def process_markets(data):
    global exchange

    exchange_class = getattr(ccxt, data['exchange_id'])
    exchange = exchange_class({'enableRateLimit': True})
    eligible_markets = []
    error_markets = []

    time_to_check_back = int(data['time_to_check_back'])
    time_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=time_to_check_back)
    parsed_time_ago = exchange.parse8601(time_ago.isoformat())

    count = 0
    for market in data['markets']:
        try:
            print(f"\rProcessing {market}, left: {len(data['markets']) - count}                    ", end='')
            ohlcv = await exchange.fetch_ohlcv(market, '1m', since=parsed_time_ago, limit=time_to_check_back)
            await exchange.close()
            
            for candle in ohlcv:
                # timestamp = candle[0]
                open_price = candle[1]  # Open price is the second item in the candle list
                high_price = candle[2]  # High price is the third item in the candle list
                # close_price = candle[4]  # Close price is the fifth item in the candle list
                volume = candle[5]  # Volume is the sixth item in the candle list
                
                # Check if the high price is 1.5 times more than the open price, 
                # and the volume changed from less than 'prev_volume' to more than 'next_volume'
                if high_price > (open_price * 1.5) and volume > data['next_volume']:
                    eligible_markets.append(market)
                    print(f"\nEligible market: {market} with open price: {open_price}, high price: {high_price}, volume: {volume}\n")
            
            count += 1

            # Send a heartbeat 
            heartbeat_payload = {'type': 'heartbeat'}
            await ws.send(json.dumps(heartbeat_payload))
        
        except Exception as e:
            print(f"\nError for market {market}: {e}\n")
            error_markets.append(market)
            await asyncio.sleep(10) 
            

    await exchange.close()

    return {'eligible_markets': eligible_markets, 'error_markets': error_markets}

async def send_response(websocket, response_data):
    response = json.dumps(response_data)
    await websocket.send(response)

async def handle_data(websocket):
    global ws
    ws = websocket
    try:
        message = await websocket.recv()
        data = json.loads(message)
        result = await process_markets(data)
        await send_response(websocket, result)

    except websockets.ConnectionClosed as e:
        logging.error(f"Connection closed: {e}")
        raise  # Re-raise to handle reconnection outside

    except Exception as e:
        print(f"An error occurred while handling data: {e}")

async def connect_to_server(uri):
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                logging.info(f"Connected to {uri}")
                while True:
                    await handle_data(websocket)
        except websockets.ConnectionClosed:
            logging.info("Connection closed, attempting to reconnect...")
        except Exception as e:
            logging.error(f"\nAn error occurred: {e}\n")
        await asyncio.sleep(10)  # Wait before retrying

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
