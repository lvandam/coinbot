import config as cfg
from binance.client import Client

class BinanceApi(object):
    def __init__(self):
        pass

    def get_tickers(self, user_id, symbols=[]):
        output = {}

        if user_id not in cfg.binance_key:
            return output

        client = Client(api_key=cfg.binance_key[user_id], api_secret=cfg.binance_secret[user_id])
        prices = client.get_all_tickers()

        for symbol in symbols:
            if len(symbol) <= 4:
                symbol_binance = symbol + "BTC"
            for price in prices:
                if price['symbol'] == symbol_binance:
                    output[symbol] = price['price']
        return output

    def balance(self, user_id):
        balance = {}

        if user_id not in cfg.binance_key:
            return balance

        client = Client(api_key=cfg.binance_key[user_id], api_secret=cfg.binance_secret[user_id])
        account = client.get_account()
        balances = account['balances']

        for asset in balances:
            if float(asset['free']) > 0 or float(asset['locked']) > 0:
                balance[asset['asset']] = float(asset['free']) + float(asset['locked'])

        return balance
