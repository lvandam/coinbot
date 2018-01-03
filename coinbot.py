#!/opt/anaconda/bin/python3
import telegram
import logging
import json
import config as cfg
from functools import wraps
import sched, time

import telegram
from telegram.utils.request import Request
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from gdax_api import GdaxApi
from bitgrail_api import BitgrailApi
from binance_api import BinanceApi

SCHEDULE_TIME = 60*60

def send_gdax(s, gdax, bot):
    chat_id = cfg.chat_id

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

        request = Request(con_pool_size=8)
        self.bot = telegram.Bot(token=cfg.bot_token, request=request)
        self.updater = Updater(bot=self.bot)
        self.dispatcher = self.updater.dispatcher

        self.gdax_api = GdaxApi()
        self.bitgrail_api = BitgrailApi()
        self.binance_api = BinanceApi()

        self.dispatcher.add_handler(CommandHandler('gdax', self.gdax, pass_args=True))
        self.dispatcher.add_handler(CommandHandler('bitgrail', self.bitgrail))
        self.dispatcher.add_handler(CommandHandler('binance', self.binance))
        self.dispatcher.add_handler(CommandHandler('balance', self.balance))
        self.dispatcher.add_handler(CommandHandler('orders', self.orders))

        self.updater.start_polling()

        # s = sched.scheduler(time.time, time.sleep)
        # s.enter(SCHEDULE_TIME, 1, send_gdax, (s,self.gdax_api,self.bot,))
        # s.run()

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
            list_coins_usd = ['BCH']
            response = "*Current rates on GDAX*\n\n"
            for symbol in list_coins_eur:
                ticker = self.gdax_api.get_ticker(symbol)
                response = response + "`%3s  €%8.2f`\n" % (symbol, round(float(ticker['price']), 2))
            for symbol in list_coins_usd:
                ticker = self.gdax_api.get_ticker(symbol+"-USD")
                response = response + "`%3s  €%8.2f`\n" % (symbol, round(float(ticker['price']), 2))
        else:
            try:
                symbol = args[0].upper()
                ticker = self.gdax_api.get_ticker(symbol)
                response = "*Current rate for %s*\n" % symbol
                response = response + "`%s`" % (ticker['price'])
            except Exception as e:
                response = "Error: %s" % str(e)

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
        prices = self.binance_api.get_tickers(user_id, ['LTC','ETH'])

    def balance(self, bot, update):
        user_id = update.effective_user.id
        logging.info("User requesting balance: " + str(user_id))

        if user_id not in cfg.key:
            return

        total = {}

        # GDAX
        balance_gdax, hold_gdax = self.gdax_api.get_balance(user_id)
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
        balance_binance = self.binance_api.balance(user_id)
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
        for currency, amount in cfg.wallet[user_id].items():
            if amount > 0:
                if currency not in total:
                    total[currency] = 0.0

                if currency in total:
                    total[currency] = total[currency] + amount
                else:
                    total[currency] = amount

        response = "*Portfolio of %s*\n\n" % update.effective_user.first_name.lower().capitalize()
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
            else: # Binance
                ticker_btc_eur = self.gdax_api.get_ticker('BTC')
                ticker = self.binance_api.get_tickers(user_id, [currency])

                value = float(ticker[currency]) * total[currency] * float(ticker_btc_eur['price'])

            if value > 0:
                response = response + "`%4s%15f%15f`\n" % (currency, total[currency], value)
                sum = sum + value

        response = response + "\n`%4s%15s€%14.2f`\n" % ("", "", round(sum, 2))
        # response = response + "\n*Total portfolio value: €%.2f*" % round(sum, 2)
        bot.send_message(chat_id=update.message.chat_id, text=response, parse_mode=telegram.ParseMode.MARKDOWN)

    def orders(self, bot, update):
        user_id = update.effective_user.id
        logging.info("User requesting orders: " + str(user_id))

        if user_id not in cfg.key:
            return

        orders = self.gdax_api.get_orders(user_id)
        orders = orders[0]

        response = "*Open orders for %s*\n\n" % update.effective_user.first_name.lower().capitalize()
        for order in orders:
            response = response + "`%7s%13s * €%8s`\n" % (order['product_id'], order['size'], round(float(order['price']), 2))

        bot.send_message(chat_id=update.message.chat_id, text=response, parse_mode=telegram.ParseMode.MARKDOWN)


if __name__ == "__main__":
    coinbot = Coinbot()
