import requests


def get_latest_eth_price(currency="USD"):
    response = requests.get("https://api.coinbase.com/v2/exchange-rates?currency=ETH")
    rates = response.json().get('data').get('rates')
    eth_to_usd = float(rates.get(currency))
    return eth_to_usd
