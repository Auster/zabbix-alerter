import logging
import subprocess

import telebot

from config import *

logging.basicConfig(format=logformat,
                    datefmt='%m/%d/%Y %H:%M:%S',
                    filename=filename,
                    level=logging.DEBUG)

cache_path = CACHE_DIR

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

@bot.message_handler(commands=['start'])
def send_welcome(message, bot=bot):
    chat_id = message.chat.id
    username = message.chat.username
    try:
        user_path = cache_path + "/" +username + '.id'
        fp = open(user_path, 'w')
        fp.truncate()
        fp.write(str(chat_id))
        fp.close()
    except Exception as err:
        print(err)
        pass

    bot.send_message(chat_id, "User added")


@bot.message_handler(commands=['help'])
def send_welcome(message, bot=bot):
    chat_id = message.chat.id
    message = """Help:
    /start
    /ping
    /ping hostname(or ip)
    /ping hostname(or ip) count
    /help
    """
    bot.send_message(chat_id, message)


@bot.message_handler(commands=['ping'])
def send_ping(message, bot=bot):
    chat_id = message.chat.id

    text = str(message.text)

    text = text.split()
    count_num = '4'

    if len(text) > 1:
        if len(text) > 2:
            count_num = str(text[2])
        dest = text[1]
        count_num = '-c ' + count_num
        response = subprocess.Popen(["ping", count_num, dest], stdout=subprocess.PIPE)
        out, err = response.communicate()
        bot.send_message(chat_id, out)

    else:
        bot.send_message(chat_id, 'pong')


def listner(bot=bot):
    bot.polling(none_stop=True)


def sender(to, subject, body, action_id):
    try:
        user_path = cache_path + "/" + to + '.id'
        with open(user_path, 'r') as user:
            chat_id = user.read()
            user.close()

    except Exception as err:
        print(err)
        return False, str(err)

    try:
        img_path = cache_path + "/" + str(action_id) + '.png'

        fp = open(img_path, 'rb')
        img = fp
        bot.send_photo(chat_id=chat_id, photo=img)
        bot.send_message(chat_id=chat_id, text=body)
        fp.close()

        return True, "ok"

    except Exception as err:
        print(err)
        logging.error(err)
        return False, str(err)