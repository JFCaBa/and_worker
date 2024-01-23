import os
import logging

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


# API Keys and Credentials
API_KEY = os.getenv('API_KEY')  
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')

# WebSocket Configuration
WS_URI = os.getenv('WS_URI')
WS_RECONNECT_ATTEMPTS = 3
WS_RECONNECT_INTERVAL = 5  # In seconds

# Exchange Client Settings
EXCHANGE_RATE_LIMIT = True
EXCHANGE_REQUEST_TIMEOUT = 10000  # In milliseconds

# Logging Configuration
LOG_FILE_PATH = './logfile.log'
LOG_LEVEL = 'INFO'

# Application Specific Constants
QUERY_DELAY = 1
MAX_QUERY_DELAY = 5.0
