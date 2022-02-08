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

USER_SHARES = {}


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
    if len(lst) == 5:
        # ['05/30/2015', '$12.0279', 'Dividend', 'Reinvestment', '4.3079']
        return {'price': float(lst[1][1:]), 'count': float(lst[4])}
    else:
        # ['11/31/2017', '$23.77', '01/05/2023', '14']
        return {'price': float(lst[1][1:]), 'count': float(lst[3])}


def parse_data(str_lines):
    return [parse_line(l) for l in str_lines.split('\n')]
    # return list(map(parse_line, str_lines.split('\n')))


def calc_profit(shares, curr_price):
    profit = sum([(curr_price - s['price']) * s['count'] for s in shares])
    return profit


# Telegram
def profit(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /profit is issued."""
    chat_id = update.message.chat.id
    curr_price = get_curr_price()

    try:
        today_profit = calc_profit(USER_SHARES[chat_id], curr_price)
        update.message.reply_text(f'Your profit today is: ${today_profit:.2f}')
        # update.message.reply_text('Your profit today is: {:.2f}'.format(today_profit))
    except KeyError:
        update.message.reply_text('You should update your shares')


def update(update: Update, context: CallbackContext) -> None:
    update_shares = update.message.text
    chat_id = update.message.chat.id

    # remove /update
    update_shares = update_shares[len('/update'):].strip()

    if update_shares == '':
        USER_SHARES[chat_id] = []
        update.message.reply_text('You have reseted all your shares')
    else:
        try:
            USER_SHARES[chat_id] = parse_data(update_shares)
            update.message.reply_text('You have update your shares')
        except IndexError:
            update.message.reply_text('Error occurred during the update')


def main() -> None:
    updater = Updater(os.environ['TOKEN'])

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("profit", profit))
    dispatcher.add_handler(CommandHandler("update", update))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
