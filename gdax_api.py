import time
import gdax

class GdaxApi(object):
    def __init__(self):
        self.ac = gdax.PublicClient()
        self.products = []

        self.get_products()

    def get_products(self):
        self.products = self.ac.get_products()

    def is_valid_product(self, product):
        for product in self.products:
            if product['id'] == product:
                return True
        return False

    def get_ticker(self, symbol):
        if "-" not in symbol:
            symbol = symbol + "-EUR"
        ticker = self.ac.get_product_ticker(product_id=symbol)
        if 'message' in ticker:
            raise Exception(ticker['message'])

        rate = self.ac.get_product_24hr_stats(symbol)
        if 'message' in rate:
            raise Exception(ticker['message'])
        ticker['open'] = float(rate['open'])

        ticker['rate'] = (float(ticker['price']) - ticker['open']) / ticker['open']
        ticker['rate_percent'] = ticker['rate'] * 100

        return ticker

    def get_change(self, symbol):
        if "-" not in symbol:
            symbol = symbol + "-EUR"

    def get_balance(self, credentials):
        ac = gdax.AuthenticatedClient(credentials['gdax_key'], credentials['gdax_b64'], credentials['gdax_pass'])
        accounts = ac.get_accounts()
        balance = {}
        hold = {}
        for entry in accounts:
            currency = entry['currency']
            balance[currency] = float(entry['balance'])
            hold[currency] = float(entry['available'])

        return (balance, hold)

    def get_orders(self, credentials):
        ac = gdax.AuthenticatedClient(credentials['gdax_key'], credentials['gdax_b64'], credentials['gdax_pass'])
        orders = ac.get_orders()
        return orders
