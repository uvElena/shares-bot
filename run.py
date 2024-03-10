import os
import requests
import json
import logging
from bs4 import BeautifulSoup
from datetime import date, datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import MessageHandler, filters, CallbackContext
from telegram.ext import CommandHandler, ApplicationBuilder


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


def get_shares_data():
    url = "https://marketwatch.com/investing/stock/csco"
    req = requests.get(
        url,
        headers={
            "User-Agent": "Firefox/47.0",
            "Accept-Language": "en-US"
        }
    )
    soup = BeautifulSoup(req.content, 'html.parser')

    # '48.73'
    curr_price_str = soup.find('bg-quote', class_="value").contents[0]

    curr_price = float(curr_price_str)

    div_data = soup.find('ul', class_="list list--kv list--col50")

    div_price_data = div_data.contents[23]
    # '$0.38'
    div_price_str = div_price_data.find('span', class_="primary").contents[0]
    div_price = float(div_price_str[1:])

    div_date_data = div_data.contents[25]
    # 'Jan 4, 2023'
    div_date_str = div_date_data.find('span', class_="primary").contents[0]
    div_date = datetime.strptime(div_date_str, "%b %d, %Y")

    return {
        'curr_price': curr_price,
        'div_price': div_price,
        'div_date': div_date,
    }


def parse_line(str_line):
    lst = str_line.split()
    # ['05/30/2015', '$12.0279', 'Dividend', 'Reinvestment', '4.3079']
    return {
        'price': float(lst[1].lstrip('$')),
        'dividend': lst[2] == 'Dividend',
        'count': float(lst[-1]),
    }


def parse_data(str_lines):
    return [parse_line(l) for l in str_lines.split('\n')]
    # return list(map(parse_line, str_lines.split('\n')))


def calc_profit(shares, curr_price):
    return sum([(curr_price - s['price']) * s['count'] for s in shares])


def calc_profit_div(shares, curr_price):
    shares_div = [s for s in shares if s['dividend']]
    shares_no_div = [s for s in shares if not s['dividend']]

    profit_div = curr_price * sum([s['count'] for s in shares_div])
    profit_no_div = calc_profit(shares_no_div, curr_price)

    return profit_div + profit_no_div


def count_total_shares(shares):
    return sum([d['count'] for d in shares])


# Telegram
def get_keyboard():
    reply_keyboard = [
        ['/help', '/show', '/profit']
    ]
    return ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


def write_shares(shares, id):
    with open(f"state/{id}.json", "w") as outfile:
        json.dump(shares, outfile)


def get_shares(id):
    try:
        with open(f'state/{id}.json') as json_file:
            return json.load(json_file)
    except (json.JSONDecodeError, FileNotFoundError):
        logger.exception("Error during file load:")
        return []


def with_reply(func):
    async def inner(update: Update, context: CallbackContext):
        message = await func(update, context)
        await update.message.reply_text(
            message, reply_markup=get_keyboard(), parse_mode=ParseMode.MARKDOWN
        )
    return inner


@with_reply
async def start(update: Update, context: CallbackContext):
    return 'Welcome to Cisco Shares Bot! Select /help to see help message.'


@with_reply
async def help_command(update: Update, context: CallbackContext):
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
async def profit(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat.id)
    actual_data = get_shares_data()
    curr_price = actual_data['curr_price']
    shares_data = get_shares(chat_id)

    shares = [

        f"| {d['count']:<7n} "
        f"| ${d['price']:<5.2f} "
        f"| {'*' if d['dividend'] else ' '} "
        f"| ${(curr_price - d['price']) * d['count']:<8.2f} |"

        for d in shares_data

    ]

    today = date.today().strftime("%d.%m.%Y")
    total_count = count_total_shares(shares_data)

    profit_total = calc_profit(shares_data, curr_price)
    profit_total_div = calc_profit_div(shares_data, curr_price)

    today_value = curr_price * total_count

    div_price = actual_data['div_price']
    div_quarter = div_price * total_count
    div_year = div_quarter * 4

    div_date = actual_data['div_date']
    # 04.01.2023
    div_date_str = datetime.strftime(div_date, "%d.%m.%Y")

    separator = '+' + '-' * 9 + '+' + '-' * 8 + '+' + '-' * 3 + '+' + '-' * 11 + '+'
    table_header = f"| {'Count':<7} | {'Price':<6} | {'D':<1} | {'Profit':<9} |"
    table_body = '\n'.join(shares)
    table_bottom = f"| {total_count:<7.2f} | ${curr_price:<5.2f} |   | ${profit_total:<8.2f} |"
    table_bottom_div = f"| {'':<7} | {'':<6} | * | ${profit_total_div:<8.2f} |"
    table = '\n'.join([
        separator,
        table_header,
        separator,
        table_body,
        separator,
        table_bottom,
        table_bottom_div,
        separator,
    ])

    return '\n'.join([
        '```',
        f'Date: {today}',
        table,
        f'Ex-dividend: {div_date_str}',
        f'Dividend Q:  ${div_quarter:<8.2f}',
        f'Dividend Y:  ${div_year:<8.2f}',
        f'Total value: ${today_value:<8.2f}',
        '```'
    ])


@with_reply
async def update(update: Update, context: CallbackContext):
    update_shares = update.message.text
    chat_id = str(update.message.chat.id)
    # remove /update
    update_shares = update_shares[len('/update'):].strip()

    if update_shares == '':
        shares_data = []
        write_shares(shares_data, chat_id)
        logger.info(f"Shares have been reset for chat_id = {chat_id}")
        return 'You have reset all your shares'
    else:
        try:
            shares_data = parse_data(update_shares)
            write_shares(shares_data, chat_id)
            return 'You have updated your shares'
        except (IndexError, ValueError):
            return 'Error occurred during the update'


@with_reply
async def show(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat.id)
    shares_data = get_shares(chat_id)

    shares = [
        f"| {d['count']:<8n} | {'*' if d['dividend'] else ' '} | ${d['price']:.2f} |"
        for d in shares_data
    ]

    table_header = f"| {'Count':<8} | {'D':<1} | Price  |"
    separator = '+' + '-' * 10 + '+' + '-' * 3 + '+' + '-' * 8 + '+'
    table_body = '\n'.join(shares)
    table = '\n'.join([
        separator, table_header, separator, table_body, separator
    ])

    return f"```\n{table}\n```"


def main() -> None:

    application = ApplicationBuilder().token(os.environ['TOKEN']).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profit", profit))
    application.add_handler(CommandHandler("update", update))
    application.add_handler(CommandHandler("show", show))

    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), help_command)
    )

    application.run_polling()


if __name__ == '__main__':
    main()
