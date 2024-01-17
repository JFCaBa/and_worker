import socket
import json
import sys
import ccxt
import time
import logging
import datetime

all_markets = []
client = None

def process_markets(data):

    # Initialize the exchange
    exchange_class = getattr(ccxt, data['exchange_id'])
    exchange = exchange_class({'enableRateLimit': True})

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
                    
                # time.sleep(0.2)

        except ccxt.RateLimitExceeded as e:
            print(f"\nRate limit exceeded: {e}\n")
            print('Sleeping for 10 seconds\n')
            # Use rateLimit info from exchange to wait the appropriate amount of time
            time.sleep(10)
            continue
        except Exception as e:
            print(f"\nError for market {market}: {e}\n")
            error_markets.append(market)
            continue

        counter += 1

        # Print your log with the time prefix
        print(f"\r{parsed_time_ago} Analysed: {market}, left: {len(data['markets']) - counter}               ", end='')


    return {'eligible_markets': eligible_markets, 'error_markets': error_markets}


def attempt_connection(host, port):
    global client
    while True:
        try:
            if client is None:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((host, port))
            print(f"Connected to {host}:{port}                                            ")
            return client  # Successfully connected
        except KeyboardInterrupt:
            print("\nInterrupted. Closing connection...\n")
            if client:
                client.close()
            client = None  # Reset client to trigger reconnection
            sys.exit(0)
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

            # print("Raw data received:", data)  # Inspect raw data

            segment = json.loads(data)

            # Process the segment
            result = process_markets(segment)

            # Send response back to the server
            send_response(client, result)
        except KeyboardInterrupt:
            print("\nInterrupted. Closing connection...\n")
            if client:
                try:
                    client.close()
                    print("Closed client connection")
                except Exception as e:
                    print(f"Error closing client connection: {e}")
            sys.exit(0)

        except (ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError):
            print("\nConnection lost. Attempting to reconnect...\n")
            if client:
                try:
                    client.close()
                    print("Closed client connection")
                except Exception as e:
                    print(f"Error closing client connection: {e}")
            continue

        except Exception as e:
            print(f"\nAn error occurred: {e}\n")
            if client:
                try:
                    client.close()
                    print("Closed client connection")
                except Exception as e:
                    print(f"Error closing client connection: {e}")
            continue

    # if client:
    #     client.close()
    # sys.exit(0)

    
def handle_error(client, markets):
    # Prepare an error response
    error_response = {'eligible_markets': [], 'error_markets': markets}
    
    # Send the error response back to the server
    send_response(client, error_response)

    client.close()
    sys.exit(0)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    connect_to_server('onedayvpn.com', 5001)
