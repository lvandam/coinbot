#!/opt/anaconda/bin/python3
import telegram
import logging
import json
import config as cfg
from functools import wraps
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from gdaxapi import GdaxApi
import sched, time

SCHEDULE_TIME = 60*60

def send_gdax(s, gdax, bot):
	chat_id = cfg.chat_id

	list_coins = ['BTC', 'ETH', 'LTC']
	response = "*Current rates on GDAX*\n"
	for symbol in list_coins:
		ticker = gdax.get_ticker(symbol)
		response = response + "`%s` - `€%.2f`\n" % (symbol, float(ticker['price']))

	bot.send_message(chat_id=chat_id, text=response, parse_mode=telegram.ParseMode.MARKDOWN)
	s.enter(SCHEDULE_TIME, 1, send_gdax, (s,gdax,bot,))
	s.run()

class Coinbot(object):
	LIST_OF_ADMINS = [12924230]

	def __init__(self):
		logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

		self.bot = telegram.Bot(token=cfg.bot_token)
		self.updater = Updater(bot=self.bot)
		self.dispatcher = self.updater.dispatcher

		self.gdax_api = GdaxApi()
		self.dispatcher.add_handler(CommandHandler('gdax', self.gdax, pass_args=True))
		self.dispatcher.add_handler(CommandHandler('balance', self.balance))

		self.updater.start_polling()

		s = sched.scheduler(time.time, time.sleep)
		s.enter(SCHEDULE_TIME, 1, send_gdax, (s,self.gdax_api,self.bot,))
		s.run()

	def restricted(func):
		@wraps(func)
		def wrapped(self, bot, update, *args, **kwargs):
			user_id = update.effective_user.id
			if user_id not in self.LIST_OF_ADMINS:
				logging.warning("%s: Unauthorized access denied for %s %s (%d)", func.__name__, update.effective_user.first_name, update.effective_user.last_name, user_id)
				return
			return func(self, bot, update, *args, **kwargs)
		return wrapped

	def gdax(self, bot, update, args):
		if len(args) == 0:
			list_coins = ['BTC', 'ETH', 'LTC']
			response = "*Current rates on GDAX*\n"
			for symbol in list_coins:
				ticker = self.gdax_api.get_ticker(symbol)
				response = response + "`%s` - `€%.2f`\n" % (symbol, float(ticker['price']))
		else:
			try:
				symbol = args[0].upper()
				ticker = self.gdax_api.get_ticker(symbol)
				response = "*Current rate for %s*\n" % symbol
				response = response + "`%s`" % (ticker['price'])
			except Exception as e:
				response = "Error: %s" % str(e)

		bot.send_message(chat_id=update.message.chat_id, text=response, parse_mode=telegram.ParseMode.MARKDOWN)

	def balance(self, bot, update):
		user_id = update.effective_user.id
		balance, hold = self.gdax_api.get_balance(user_id)

		response = ''
		sum = 0.0
		for currency, data in balance.items():
			if currency == 'EUR':
				value = balance[currency]
				total = value
				holds = 0
			else:
				ticker = self.gdax_api.get_ticker(currency)
				value = float(ticker['price']) * balance[currency]
				total = balance[currency]
				holds = hold[currency]
			sum = sum + value

			response = response + "`%3s%15f%20s%15f`\n" % (currency, total, "("+str(holds)+")", value)
		response = response + "\n*Total portfolio value: €%.2f*" % round(sum, 2)
		bot.send_message(chat_id=update.message.chat_id, text=response, parse_mode=telegram.ParseMode.MARKDOWN)

if __name__ == "__main__":
	coinbot = Coinbot()
