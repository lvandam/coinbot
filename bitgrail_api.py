from time import time
import hashlib
import hmac
import urllib3, certifi, json
import urllib.parse

class BitgrailApi(object):
	def __init__(self):
		pass

	def last_price(self):
		bitgrail_price = 'https://api.bitgrail.com/v1/BTC-XRB/ticker'

		http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',ca_certs=certifi.where())
		#response = http.request('GET', bitgrail_price, headers=header, timeout=20.0)
		response = http.request('GET', bitgrail_price, timeout=20.0)
		json_bitgrail = json.loads(response.data)
		json_array = json_bitgrail['response']
		last_price = float(json_array['last'])

		volume = int(float(json_array['coinVolume']))
		btc_volume = int(float(json_array['volume']) * (10 ** 8))

		return float(last_price)

	def balance(self, credentials):
		bitgrail_balances = 'https://api.bitgrail.com/v1/balances'

		key = credentials['bitgrail_key'].encode('utf-8')
		secret = credentials['bitgrail_secret'].encode('utf-8')
		http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',ca_certs=certifi.where())

		payload = {'nonce': int(time() * 1000)}
		paybytes = urllib.parse.urlencode(payload).encode('utf-8')
		signature = hmac.new(secret, paybytes, hashlib.sha512).hexdigest()
		headers = {'KEY': key, 'SIGNATURE': signature, 'Content-Type': 'application/x-www-form-urlencoded'}

		response = http.request('POST', bitgrail_balances, headers=headers, fields=payload, timeout=20.0)

		json_bitgrail = json.loads(response.data)

		print(json_bitgrail)
		json_array = json_bitgrail['response']

		balance = float(json_array['balance'])

		print(balance)
