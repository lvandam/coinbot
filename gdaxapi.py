import config as cfg
import gdax

class GdaxApi(object):
	def __init__(self):
		self.ac = gdax.AuthenticatedClient(cfg.key, cfg.b64secret, cfg.passphrase)
		self.products = []

		self.balance = {}
		self.hold = {}

		self.get_products()

	def get_products(self):
		self.products = self.ac.get_products()

	def is_valid_product(self, product):
		for product in self.products:
			print(product['id'])
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
		for entry in accounts:
			currency = entry['currency']
			self.balance[currency] = float(entry['balance'])
			self.hold[currency] = float(entry['available'])

		for currency, value in cfg.wallet[user_id].items():
			self.balance[currency] = self.balance[currency] + value

		return (self.balance, self.hold)
