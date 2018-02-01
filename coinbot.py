#!/opt/anaconda/bin/python3
import telegram
import pymongo
from pymongo import MongoClient
import logging
import json
import config as cfg
from functools import wraps
import sched, time
import pprint

import telegram
from telegram.utils.request import Request
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from gdax_api import GdaxApi
from bitgrail_api import BitgrailApi
from binance_api import BinanceApi
from bittrex_api import BittrexApi

SCHEDULE_TIME = 60*60

def send_gdax(s, chat_id, gdax, bot):
    list_coins = ['BTC', 'ETH', 'LTC']
    response = "*Current rates on GDAX*\n"
    for symbol in list_coins:
        ticker = gdax.get_ticker(symbol)
        response = response + "`%5s €%8f`\n" % (symbol, float(ticker['price']))

    bot.send_message(chat_id=chat_id, text=response, parse_mode=telegram.ParseMode.MARKDOWN)
    s.enter(SCHEDULE_TIME, 1, send_gdax, (s,gdax,bot,))
    s.run()

class Coinbot(object):
    LIST_OF_ADMINS = [12924230]

    def __init__(self):
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

        self.mongoc = MongoClient(cfg.mongodb_host, username=cfg.mongodb_user, password=cfg.mongodb_pass, authSource='coinbot', authMechanism='SCRAM-SHA-1')
        self.db = self.mongoc[cfg.mongodb_db]

        self.chat_id, self.bot_token = self.load_config()

        request = Request(con_pool_size=8)
        self.bot = telegram.Bot(token=self.bot_token, request=request)
        self.updater = Updater(bot=self.bot)
        self.dispatcher = self.updater.dispatcher

        self.gdax_api = GdaxApi()
        self.bitgrail_api = BitgrailApi()
        self.binance_api = BinanceApi()
        self.bittrex_api = BittrexApi()

        self.dispatcher.add_handler(CommandHandler('gdax', self.gdax, pass_args=True))
        self.dispatcher.add_handler(CommandHandler('change', self.change, pass_args=True))
        self.dispatcher.add_handler(CommandHandler('bitgrail', self.bitgrail))
        self.dispatcher.add_handler(CommandHandler('binance', self.binance))
        self.dispatcher.add_handler(CommandHandler('balance', self.balance, pass_args=True))
        self.dispatcher.add_handler(CommandHandler('orders', self.orders))

        self.updater.start_polling()

    def load_config(self):
        config_db = self.db['config']
        config_row = config_db.find_one()

        chat_id = config_row['private']['telegram_chat_id']
        bot_token = config_row['private']['telegram_bot_token']

        return chat_id, bot_token

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
            list_coins_eur = ['BTC', 'ETH', 'LTC']
            list_coins_usd = []#['BCH']
            response = "*Current rates on GDAX*\n\n"
            for symbol in list_coins_eur:
                ticker = self.gdax_api.get_ticker(symbol)
                response = response + "`%3s  €%8.2f  %5.2f%%`\n" % (symbol, round(float(ticker['price']), 2), round(ticker['rate_percent'], 2))
            for symbol in list_coins_usd:
                ticker = self.gdax_api.get_ticker(symbol+"-USD")
                response = response + "`%3s  $%8.2f  %5.2f%%`\n" % (symbol, round(float(ticker['price']), 2), round(ticker['rate_percent'], 2))
        else:
            try:
                symbol = args[0].upper()
                ticker = self.gdax_api.get_ticker(symbol)
                response = "*Current rate for %s*\n" % symbol
                response = response + "`%s`" % (ticker['price'])
            except Exception as e:
                response = "Error: %s" % str(e)

        bot.send_message(chat_id=update.message.chat_id, text=response, parse_mode=telegram.ParseMode.MARKDOWN)

    def change(self, bot, update, args):
        if len(args) == 0:
            symbol = 'BTC-EUR'
        else:
            symbol = args[0].upper()

        rates = self.gdax_api.get_change(symbol)

        bot.send_message(chat_id=update.message.chat_id, text=response, parse_mode=telegram.ParseMode.MARKDOWN)

    def bitgrail(self, bot, update):
        last_price = self.bitgrail_api.last_price()

        gdax_btc_eur = self.gdax_api.get_ticker('BTC')

        response = "*Current rate on Bitgrail*\n"
        response = response + "`XRB  %1.8f BTC`\n" % last_price
        response = response + "`    €%.2f`\n" % round(float(gdax_btc_eur['price']) * last_price, 2)
        bot.send_message(chat_id=update.message.chat_id, text=response, parse_mode=telegram.ParseMode.MARKDOWN)

    def binance(self, bot, update):
        user_id = update.effective_user.id
        symbols = ['XRP','IOTA','REQ','POE']
        prices = self.binance_api.get_tickers(user_id, symbols)
        gdax_btc_eur = self.gdax_api.get_ticker('BTC')
        response = "*Current rates on Binance*\n\n"
        for symbol in symbols:
            response = response + "`%4s  %8f BTC  €%.2f`\n" % (symbol, float(prices[symbol]), round(float(gdax_btc_eur['price']) * float(prices[symbol]), 2))
        bot.send_message(chat_id=update.message.chat_id, text=response, parse_mode=telegram.ParseMode.MARKDOWN)



    def balance(self, bot, update, args=[]):
        if len(args) > 0:
            user = self.db['users'].find_one({'name': args[0].lower()})
        else:
            user = self.db['users'].find_one({'telegram_id': update.effective_user.id})

        if user == None:
            return

        user_id = user['telegram_id']
        name = user['name']

        logging.info("User requesting balance for " + name.capitalize() + " ("+str(user_id)+")")

        total = {}

        # GDAX
        credentials = self.get_gdax_credentials(user_id)
        balance_gdax, hold_gdax = self.gdax_api.get_balance(credentials)
        for currency, data in balance_gdax.items():
            if currency not in total:
                total[currency] = 0.0

            if currency == 'EUR':
                total[currency] = total[currency] + balance_gdax[currency]
            else:
                if currency == 'BCH':
                    continue
                total[currency] = total[currency] + balance_gdax[currency]

        # Binance
        credentials = self.get_binance_credentials(user_id)
        balance_binance = self.binance_api.balance(credentials)
        for currency, value in balance_binance.items():
            if currency not in total:
                total[currency] = 0.0

            if currency == 'EUR':
                total[currency] = total[currency] + value
            else:
                total[currency] = total[currency] + value

        # Bitgrail
        # balance_bitgrail = self.bitgrail_api.balance(user_id)

        # Wallets
        wallet = self.db['wallet'].find_one({'user': user['_id']})
        if wallet is not None:
            for currency, amount in wallet['currencies'].items():
                if amount > 0:
                    if currency not in total:
                        total[currency] = 0.0

                    if currency in total:
                        total[currency] = total[currency] + amount
                    else:
                        total[currency] = amount

        response = "*Portfolio of %s*\n\n" % name.capitalize()
        response = response + "`%4s%15s%15s`\n" % ("", "", "€")

        sum = 0.0
        for currency in total:
            if currency == 'EUR':
                value = total[currency]
            elif currency == 'XRB': # XRB: Bitgrail
                ticker_btc_eur = self.gdax_api.get_ticker('BTC')
                ticker_xrb = self.bitgrail_api.last_price()
                xrb_eur = ticker_xrb * float(ticker_btc_eur['price'])
                value = xrb_eur * total[currency]
            elif currency == 'BCH':
                continue
            elif currency in ('BTC', 'LTC', 'ETH'):
                ticker = self.gdax_api.get_ticker(currency)
                value = float(ticker['price']) * total[currency]
            elif currency in ('EMC'):
                ticker = self.bittrex_api.get_ticker(currency)
                ticker_btc_eur = self.gdax_api.get_ticker('BTC')
                emc_eur = ticker['Last'] * float(ticker_btc_eur['price'])
                value = emc_eur * total[currency]
            else: # Binance
                ticker_btc_eur = self.gdax_api.get_ticker('BTC')
                credentials = self.get_binance_credentials(user_id)
                ticker = self.binance_api.get_tickers(credentials, [currency])

                value = float(ticker[currency]) * total[currency] * float(ticker_btc_eur['price'])

            if value > 0:
                response = response + "`%4s%15f%15f`\n" % (currency, total[currency], value)
                sum = sum + value

        response = response + "\n`%4s%15s€%14.2f`\n" % ("", "", round(sum, 2))
        bot.send_message(chat_id=update.message.chat_id, text=response, parse_mode=telegram.ParseMode.MARKDOWN)

    def get_gdax_credentials(self, user_id):
        credentials = self.db['users'].find_one({'telegram_id': user_id}, {'_id': 0, 'gdax_key': 1, 'gdax_b64': 1, 'gdax_pass': 1})
        if credentials is not None:
            return credentials
        else:
            logging.error("No user found for Telegram ID %d", user_id)

    def get_binance_credentials(self, user_id):
        credentials = self.db['users'].find_one({'telegram_id': user_id}, {'_id': 0, 'binance_key': 1, 'binance_secret': 1})
        if credentials is not None:
            return credentials
        else:
            logging.error("No user found for Telegram ID %d", user_id)

    def orders(self, bot, update):
        user_id = update.effective_user.id
        logging.info("User requesting orders: " + str(user_id))

        credentials = self.get_gdax_credentials(user_id)
        orders = self.gdax_api.get_orders(credentials)
        orders = orders[0]

        response = "*Open orders for %s*\n\n" % update.effective_user.first_name.lower().capitalize()
        for order in orders:
            response = response + "`%7s%13s * €%8s`\n" % (order['product_id'], order['size'], round(float(order['price']), 2))

        bot.send_message(chat_id=update.message.chat_id, text=response, parse_mode=telegram.ParseMode.MARKDOWN)


if __name__ == "__main__":
    coinbot = Coinbot()
