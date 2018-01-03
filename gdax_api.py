import config as cfg
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

        return ticker

    def get_balance(self, user_id):
        ac = gdax.AuthenticatedClient(cfg.key[user_id], cfg.b64secret[user_id], cfg.passphrase[user_id])

        accounts = ac.get_accounts()
        balance = {}
        hold = {}
        for entry in accounts:
            currency = entry['currency']
            balance[currency] = float(entry['balance'])
            hold[currency] = float(entry['available'])

        return (balance, hold)

    def get_orders(self, user_id):
        ac = gdax.AuthenticatedClient(cfg.key[user_id], cfg.b64secret[user_id], cfg.passphrase[user_id])

        orders = ac.get_orders()

        return orders
