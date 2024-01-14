import asyncio
import ccxt.pro as ccxtpro  # Use CCXT Pro for async support
import ccxt  # Standard CCXT
import json
import socket
import sys
import datetime
import time

all_markets = []

async def process_markets(data):
    exchange_id = data['exchange_id']
    time_to_check_back = int(data['time_to_check_back'])
    time_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=time_to_check_back)
    parsed_time_ago = int(time_ago.timestamp() * 1000)

    if hasattr(ccxtpro, exchange_id):
        # Asynchronous processing with CCXT Pro
        exchange = getattr(ccxtpro, exchange_id)({'enableRateLimit': True})
        return await process_markets_async(exchange, data, parsed_time_ago)
    else:
        # Synchronous processing with standard CCXT
        exchange = getattr(ccxt, exchange_id)({'enableRateLimit': True})
        return process_markets_sync(exchange, data, parsed_time_ago)

async def process_markets_async(exchange, data, since):
    # Asynchronous market processing logic
    eligible_markets = []
    error_markets = []
    counter = 0
    for market in data['markets']:
        try:
            ohlcv = await exchange.fetch_ohlcv(market, '1m', since=since)
            # Process OHLCV data
            for candle in ohlcv:
                open_price = candle[1]  # Open price is the second item in the candle list
                high_price = candle[2]
                close_price = candle[4]  # Close price is the fifth item in the candle list
                
                # Check if the open price is less than 1, the close price is higher than the open, 
                # and the volume changed from less than 'prev_volume' to more than 'next_volume'
                if high_price > (open_price * 1.5):
                    eligible_markets.append(market)
                    print(f"Eligible market: {market} with open price {open_price}, high price {close_price}")
                    break  # Stop checking further candles since condition is met
            
            await asyncio.sleep(0.2)  # Corrected to await the sleep call
        except Exception as e:
            print(f"Error for market {market}: {e}")
            error_markets.append(market)

        counter += 1
        print(f"Analysed: {market}, left: {len(data['markets']) - counter}")

    return {'eligible_markets': eligible_markets, 'error_markets': error_markets}


def process_markets_sync(exchange, data, since):
    # Synchronous market processing logic
    # Example: Fetch OHLCV data synchronously
    eligible_markets = []
    error_markets = []
    counter = 0
    for market in data['markets']:
        try:
            ohlcv = exchange.fetch_ohlcv(market, '1m', since=since)
            # Process ohlcv data
            for candle in ohlcv:
                open_price = candle[1]  # Open price is the second item in the candle list
                high_price = candle[2]
                close_price = candle[4]  # Close price is the fifth item in the candle list
                
                # Check if the open price is less than 1, the close price is higher than the open, 
                # and the volume changed from less than 'prev_volume' to more than 'next_volume'
                if high_price > (open_price * 1.5):
                    eligible_markets.append(market)
                    print(f"Eligible market: {market} with open price {open_price}, high price {close_price}")
                    break  # Stop checking further candles since condition is met
            
            time.sleep(0.2)
        except Exception as e:
            print(f"Error for market {market}: {e}")
            error_markets.append(market)

        counter += 1
        print(f"Analysed: {market}, left: {len(data['markets']) - counter}")

    return {'eligible_markets': eligible_markets, 'error_markets': error_markets}


def attempt_connection(host, port):
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((host, port))
            print(f"Connected to {host}:{port}")
            return client  # Successfully connected
        except ConnectionResetError:
            print("Connection reset. Trying to connect in 10 seconds...")
            time.sleep(10)
        except ConnectionRefusedError:
            print(f"Connection to {host}:{port} failed. Retrying in 10 seconds...")
            time.sleep(10)  # Wait for 10 seconds before retrying
        except Exception as e:
            print(f"An error occurred: {e}")

def send_response(client, response_data):    # Convert the response to JSON and encode it
    # Convert the response to JSON and encode it
    response = json.dumps(response_data).encode('utf-8')

    # Send the length of the response first
    response_length = str(len(response)).encode('utf-8')
    client.sendall(response_length + b'\n')

    # Send the actual response data
    client.sendall(response)
    print(f"[Debug] Sent response: {response_data}")  # Debugging line


async def async_attempt_connection(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    print(f"Connected to {host}:{port}")
    return reader, writer


async def connect_to_server(host, port):
    reader, writer = None, None
    while True:
        try:
            if reader is None or writer is None:
                reader, writer = await async_attempt_connection(host, port)

            # Receiving data
            data_length_str = await reader.readuntil(separator=b'\n')
            data_length = int(data_length_str.decode('utf-8').strip())

            # Initialize an empty data buffer
            data = bytearray()
            while len(data) < data_length:
                chunk = await reader.read(1024)
                if not chunk:
                    # No more data, break the loop
                    break
                data.extend(chunk)

            # Process the segment asynchronously
            segment = json.loads(data.decode('utf-8'))
            result = await process_markets(segment)

            response = json.dumps(result).encode('utf-8')

            # Include newline character in the length
            response_length = len(response) + 1
            response_header = f"{response_length}\n".encode('utf-8')

            writer.write(response_header + response)
            await writer.drain()

            # Do not immediately close the connection, allow some time for the server to read
            await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("\nInterrupted. Closing connection...")
            if writer is not None:
                writer.close()
                await writer.wait_closed()
                reader, writer = None, None
            break
        except (ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError):
            print("\rConnection lost. Attempting to reconnect...", end='')
            if writer is not None:
                writer.close()
                await writer.wait_closed()
                reader, writer = None, None
            continue
        except Exception as e:
            print(f"An error occurred: {e}")
            if writer is not None:
                writer.close()
                await writer.wait_closed()
                reader, writer = None, None
            continue
        # finally:
        #     if writer is not None:
        #         writer.close()
        #         await writer.wait_closed()


def handle_error(client, markets):
    # Prepare an error response
    error_response = {'eligible_markets': [], 'error_markets': markets}
    
    # Send the error response back to the server
    send_response(client, error_response)

    # client.close()
    # sys.exit(0)

if __name__ == "__main__":
    asyncio.run(connect_to_server('onedayvpn.com', 5001))