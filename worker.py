import socket
import json
import sys
import ccxt
import datetime
import time

all_markets = []

def process_markets(data):

    print(f"Processing data for exchange {data['exchange_id']}")

    # Initialize the exchange
    exchange_class = getattr(ccxt, data['exchange_id'])
    exchange = exchange_class({'enableRateLimit': False})

    eligible_markets = []  # Initialize the list
    error_markets = []     # Initialize the list
    counter = 0

    # Calculate the time based on time_to_check_back
    # Convert time_to_check_back from string to integer
    time_to_check_back = int(data['time_to_check_back'])
    time_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=time_to_check_back)
    parsed_time_ago = exchange.parse8601(time_ago.isoformat())

    for market in data['markets']:
        try:
            ohlcv = exchange.fetch_ohlcv(market, '1m', since=parsed_time_ago, limit=time_to_check_back)
            
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

        except ccxt.RateLimitExceeded as e:
            print(f"Rate limit exceeded: {e}")
            # Use rateLimit info from exchange to wait the appropriate amount of time
            time.sleep(10)
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
        except ConnectionRefusedError:
            print(f"Connection to {host}:{port} failed. Retrying in 10 seconds...")
            time.sleep(10)  # Wait for 10 seconds before retrying
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(10)  # Retry after a short delay

def send_response(client, response_data):    # Convert the response to JSON and encode it
    response = json.dumps(response_data).encode('utf-8')

    # Send the length of the response first
    response_length = str(len(response)).encode('utf-8')
    client.sendall(response_length + b'\n')

    # Send the actual response data
    client.sendall(response)

def connect_to_server(host, port):
    client = None
    while True:
        try:
            if client is None:
                client = attempt_connection(host, port)
            # First receive the length of the data up to the newline
            data_length_str = ''
            char = ''
            while char != '\n':
                char = client.recv(1).decode('utf-8')
                if char != '\n':
                    data_length_str += char

            data_length = int(data_length_str)
            data_received = 0
            data = ''

            # Keep receiving data until the full length is received
            while data_received < data_length:
                part = client.recv(1024).decode('utf-8')
                data += part
                data_received += len(part)

            print("Raw data received:", data)  # Inspect raw data

            segment = json.loads(data)

            # Process the segment
            result = process_markets(segment)

            # Send response back to the server
            send_response(client, result)
        except KeyboardInterrupt:
            print("\nInterrupted. Closing connection...")
            break

        except (ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError):
            print("Connection lost. Attempting to reconnect...")
            if client:
                client.close()
            client = None  # Reset client to trigger reconnection
            continue

        except Exception as e:
            print(f"An error occurred: {e}")
            if client:
                client.close()
            client = None  # Reset client to trigger reconnection
            continue

        finally:
            if client:
                client.close()
                client = None

    if client:
        client.close()
    sys.exit(0)

    
def handle_error(client, markets):
    # Prepare an error response
    error_response = {'eligible_markets': [], 'error_markets': markets}
    
    # Send the error response back to the server
    send_response(client, error_response)

    client.close()
    sys.exit(0)



# Connect to the server and start processing
connect_to_server('54.38.215.128', 5001)