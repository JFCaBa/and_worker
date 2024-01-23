import asyncio
from exchange.exchange_client import ExchangeClient
from data_processors.pnd_candidate_checker import PNDCandidateChecker
from data_processors.market_processor import MarketProcessor
import websockets
import json
import logging
import settings

async def websocket_client(pnd_checker, market_processor):
    async with websockets.connect(settings.WS_URI) as websocket:
        logging.info(f"Connected to {settings.WS_URI}")
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                
                # Process the received data based on the task
                if data['task'] == 'process_market_data':
                    result = await market_processor.process_markets(data)
                elif data['task'] == 'check_pnd_candidates':
                    result = await pnd_checker.check(data)
                else:
                    result = {'error': 'Unknown task'}

                # Send the result back through the WebSocket
                await websocket.send(json.dumps(result))
                
            except websockets.ConnectionClosed:
                logging.error("WebSocket connection closed")
                break
            except Exception as e:
                logging.error(f"An error occurred: {e}")


async def main():
    exchange_client = ExchangeClient()  # Handles exchange initialization and other related tasks
    pnd_checker = PNDCandidateChecker(exchange_client)  # Initialize PnD checker with the exchange client
    market_processor = MarketProcessor(exchange_client)

    # Initialize other processors as needed

    while True:
        try:
            # Connect to the WebSocket server and start processing data
            await websocket_client(pnd_checker, market_processor)
        except websockets.ConnectionClosed:
            logging.error("WebSocket connection closed, attempting to reconnect...")
        except Exception as e:
            logging.error(f"An error occurred: {e}")
        await asyncio.sleep(10)  # Wait before attempting to reconnect

if __name__ == "__main__":

    if settings.WALLET_ADDRESS:
        print(f"Wallet Address: {settings.WALLET_ADDRESS}")
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nWorker stopped manually\n")
            # Perform any cleanup if needed
        except Exception as e:
            print(f"\nError in worker: {e}\n")
    else:
        print("No wallet address provided.")
