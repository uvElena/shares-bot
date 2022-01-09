import os
import requests
from bs4 import BeautifulSoup
import logging

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def get_curr_price():
    url = "https://marketwatch.com/investing/stock/csco"
    req = requests.get(url)
    soup = BeautifulSoup(req.content, 'html.parser')
    # <bg-quote channel="/zigman2/quotes/209509471/composite,/zigman2/quotes/209509471/lastsale" class="value" field="Last" format="0,0.00" session="pre">63.38</bg-quote>
    curr_price = soup.find('bg-quote', class_="value").contents
    curr_price = float(curr_price[0])
    return curr_price


def parse_line(str_line):
    lst = str_line.split()
    # ['07/30/2021', '$55.0269', 'Dividend', 'Reinvestment', '1.3028']
    return {'price': float(lst[1][1:]), 'count': float(lst[4])}


def parse_data(str_lines):
    return [parse_line(l) for l in str_lines.split('\n')]
    # return list(map(parse_line, str_lines.split('\n')))


def calc_profit(filename, curr_price):
    with open(filename, "r") as file:
        shares_str = file.read().strip()
    purchases = parse_data(shares_str)
    profit = sum([(curr_price - p['price']) * p['count'] for p in purchases])
    return profit


# Telegram
def profit(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /profit is issued."""
    curr_price = get_curr_price()
    today_profit = calc_profit("Shares.txt", curr_price)
    # update.message.reply_text('Your profit today is: {:.2f}'.format(today_profit))
    update.message.reply_text(f'Your profit today is: ${today_profit:.2f}')


def main() -> None:
    updater = Updater(os.environ['TOKEN'])

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("profit", profit))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
