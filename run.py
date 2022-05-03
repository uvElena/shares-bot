import os
import requests
from bs4 import BeautifulSoup
import logging
import collections
from datetime import date

from telegram import Update, ReplyKeyboardMarkup, ParseMode
from telegram.ext import MessageHandler, Filters, CallbackContext
from telegram.ext import Updater, CommandHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

USER_SHARES = collections.defaultdict(list)


def get_curr_price():
    url = "https://marketwatch.com/investing/stock/csco"
    req = requests.get(url)
    soup = BeautifulSoup(req.content, 'html.parser')
    # <bg-quote
    # channel="/zigman2/quotes/209509471/composite,/zigman2/quotes/209509471/lastsale"
    # class="value" field="Last" format="0,0.00" session="pre">63.38</bg-quote>
    curr_price = soup.find('bg-quote', class_="value").contents
    curr_price = float(curr_price[0])
    return curr_price


def parse_line(str_line):
    lst = str_line.split()
    # ['05/30/2015', '$12.0279', 'Dividend', 'Reinvestment', '4.3079']
    return {'price': float(lst[1].lstrip('$')), 'count': float(lst[-1])}


def parse_data(str_lines):
    return [parse_line(l) for l in str_lines.split('\n')]
    # return list(map(parse_line, str_lines.split('\n')))


def calc_profit(shares, curr_price):
    profit = sum([(curr_price - s['price']) * s['count'] for s in shares])
    return profit


# Telegram
def get_keyboard():
    reply_keyboard = [
        ['/help', '/show', '/profit']
    ]
    return ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


def with_reply(func):
    def inner(update: Update, context: CallbackContext):
        message = func(update, context)
        update.message.reply_text(
            message, reply_markup=get_keyboard(), parse_mode=ParseMode.MARKDOWN
        )
    return inner


@with_reply
def start(update: Update, context: CallbackContext):
    return 'Welcome to Cisco Shares Bot! Select /help to see help message.'


@with_reply
def help_command(update: Update, context: CallbackContext):
    return '''
/help - show help message and commands description
/show - show current shares
/profit - calculate your profit
/update - update or reset shares. Example:
```
    /update
    01/31/2011   $63.37   01/05/2012 13
```'''


@with_reply
def profit(update: Update, context: CallbackContext):
    chat_id = update.message.chat.id
    curr_price = get_curr_price()
    today_profit = calc_profit(USER_SHARES[chat_id], curr_price)

    shares = [
        f"| {d['count']:<8n} "
        f"| ${d['price']:<8.2f} "
        f"| ${(curr_price - d['price']) * d['count']:<8.2f} |"
        for d in USER_SHARES[chat_id]
    ]

    table_header = f"| {'Count':<8} | {'Price':<9} | {'Profit':<9} |"
    separator = '+' + '-' * 10 + '+' + '-' * 11 + '+' + '-' * 11 + '+'
    table_body = '\n'.join(shares)
    table = '\n'.join([
        separator, table_header,
        separator, table_body,
        separator,
    ])

    today = date.today().strftime("%d.%m.%Y")
    return '\n'.join([
        '```',
        table,
        f'Date: {today}',
        f'Current price: ${curr_price:<8.2f}',
        f'Total profit: ${today_profit:<8.2f}',
        '```'
    ])


@with_reply
def update(update: Update, context: CallbackContext):
    update_shares = update.message.text
    chat_id = update.message.chat.id

    # remove /update
    update_shares = update_shares[len('/update'):].strip()

    if update_shares == '':
        USER_SHARES[chat_id] = []
        return 'You have reset all your shares'
    else:
        try:
            USER_SHARES[chat_id] = parse_data(update_shares)
            return 'You have updated your shares'
        except (IndexError, ValueError):
            return 'Error occurred during the update'


@with_reply
def show(update: Update, context: CallbackContext):
    chat_id = update.message.chat.id

    shares = [
        f"| {d['count']:<8n} | ${d['price']:.2f} |"
        for d in USER_SHARES[chat_id]
    ]

    table_header = f"| {'Count':<8} | Price  |"
    separator = '+' + '-' * 10 + '+' + '-' * 8 + '+'
    table_body = '\n'.join(shares)
    table = '\n'.join([
        separator, table_header, separator, table_body, separator
    ])

    return f"```\n{table}\n```"


def main() -> None:
    updater = Updater(os.environ['TOKEN'])
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("profit", profit))
    dispatcher.add_handler(CommandHandler("update", update))
    dispatcher.add_handler(CommandHandler("show", show))

    dispatcher.add_handler(
        MessageHandler(Filters.text & ~Filters.command, help_command)
    )

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
