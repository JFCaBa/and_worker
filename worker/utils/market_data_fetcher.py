import aiohttp

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
                market_cap = data['data'][symbol]['quote'][quote_currency]['market_cap']
                return market_cap
            else:
                print(f"Error fetching market cap: {response.status}")
                return None
