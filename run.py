import os
import requests
from bs4 import BeautifulSoup
import logging

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import ParseMode


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

USER_SHARES = {}


def get_curr_price():
    url = "https://marketwatch.com/investing/stock/csco"
    req = requests.get(url)
    soup = BeautifulSoup(req.content, 'html.parser')
    # <bg-quote channel="/zigman2/quotes/209509471/composite,/zigman2/quotes/209509471/lastsale"
    # class="value" field="Last" format="0,0.00" session="pre">63.38</bg-quote>
    curr_price = soup.find('bg-quote', class_="value").contents
    curr_price = float(curr_price[0])
    return curr_price


def parse_line(str_line):
    lst = str_line.split()
    # ['05/30/2015', '$12.0279', 'Dividend', 'Reinvestment', '4.3079']
    return {'price': float(lst[1][1:]), 'count': float(lst[-1])}


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


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Welcome to Cisco Shares Bot! Select /help to see help message.',
        reply_markup=get_keyboard()
    )


def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        '''
/help - show help message commands description
/show - show current shares
/profit - calculate your profit
/update - update or reset shares. Example:
```
    /update
    01/31/2011   $63.37   01/05/2012 13
```''',
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_keyboard()
    )


def profit(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    curr_price = get_curr_price()
    try:
        today_profit = calc_profit(USER_SHARES[chat_id], curr_price)
        update.message.reply_text(
            f'Your profit today is: ${today_profit:.2f}',
            reply_markup=get_keyboard()
        )
    except KeyError:
        update.message.reply_text(
            'You should update your shares',
            reply_markup=get_keyboard()
        )


def update(update: Update, context: CallbackContext) -> None:
    update_shares = update.message.text
    chat_id = update.message.chat.id

    # remove /update
    update_shares = update_shares[len('/update'):].strip()

    if update_shares == '':
        USER_SHARES[chat_id] = []
        update.message.reply_text(
            'You have reseted all your shares',
            reply_markup=get_keyboard()
        )
    else:
        try:
            USER_SHARES[chat_id] = parse_data(update_shares)
            update.message.reply_text(
                'You have update your shares',
                reply_markup=get_keyboard()
            )
        except IndexError:
            update.message.reply_text(
                'Error occurred during the update',
                reply_markup=get_keyboard()
            )


def show(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    try:
        shares = [f"| {d['count']:<8n} | ${d['price']:.2f} |" for d in USER_SHARES[chat_id]]

        table_header = f"| {'Count':<8} | Price  |"
        separator = '+' + '-' * 10 + '+' + '-' * 8 + '+'
        table_body = '\n'.join(shares)
        table = '\n'.join([separator, table_header, separator, table_body, separator])

        update.message.reply_text(
            f"```\n{table}\n```",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_keyboard()
        )
    except KeyError:
        update.message.reply_text(
            'You should update your shares',
            reply_markup=get_keyboard()
        )


def main() -> None:
    updater = Updater(os.environ['TOKEN'])
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("profit", profit))
    dispatcher.add_handler(CommandHandler("update", update))
    dispatcher.add_handler(CommandHandler("show", show))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
