from binance.client import Client

class BinanceApi(object):
    def __init__(self):
        pass

    def get_tickers(self, credentials, symbols=[]):
        output = {}

        if 'binance_key' not in credentials:
            return balance

        client = Client(api_key=credentials['binance_key'], api_secret=credentials['binance_secret'])
        prices = client.get_all_tickers()

        for symbol in symbols:
            if len(symbol) <= 4:
                symbol_binance = symbol + "BTC"
            for price in prices:
                if price['symbol'] == symbol_binance:
                    output[symbol] = price['price']
        return output

    def balance(self, credentials):
        balance = {}

        if 'binance_key' not in credentials:
            return balance

        client = Client(api_key=credentials['binance_key'], api_secret=credentials['binance_secret'])
        account = client.get_account()
        balances = account['balances']

        for asset in balances:
            if float(asset['free']) > 0 or float(asset['locked']) > 0:
                balance[asset['asset']] = float(asset['free']) + float(asset['locked'])

        return balance
