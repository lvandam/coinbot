from bittrex.bittrex import Bittrex, API_V2_0, API_V1_1

class BittrexApi(object):
	def __init__(self):
		self.api = Bittrex(None, None, api_version=API_V1_1)

	def get_ticker(self, symbol):
		if len(symbol) <= 4:
			symbol = "BTC-" + symbol            
		ticker = self.api.get_ticker(symbol)

		if ticker['success']:
			return ticker['result']
		else:
			return False
